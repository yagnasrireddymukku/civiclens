"""Shared real-PostgreSQL test infrastructure.

As of Phase 5, the migration chain unconditionally runs
`CREATE EXTENSION IF NOT EXISTS pg_trgm` (search_documents needs it for
typo-tolerant matching), so *any* test that migrates a database from
scratch to `head` needs a Postgres build that ships the `pg_trgm` contrib
module. `pgserver` (the pip-installable embedded Postgres formerly used
here, see git history) does not bundle it on Windows — verified directly:
its Windows build only ships `plpgsql` and `vector`
(`.venv/*/pgserver/pginstall/share/postgresql/extension/`). Docker isn't
available in this development environment (no Docker/WSL2), so this
module manages a full PostgreSQL server (EnterpriseDB's no-installer
Windows ZIP distribution, which ships every contrib module) via plain
`initdb`/`pg_ctl` subprocesses.

Two ways to get a full Postgres, checked in order by the `full_pg_database_url`
fixture (tests/conftest.py):
1. `CIVICLENS_TEST_FULL_PG_URL` — a ready-to-use connection string (CI sets
   this to a `postgres:16` service container, which ships every contrib
   module and needs none of the machinery below).
2. A local full-PostgreSQL binary distribution, spun up per test session —
   the path this development environment uses.

Production and every deployed environment remain plain PostgreSQL per
ADR-004 either way; this is purely a test-execution detail.
"""

import os
import shutil
import socket
import subprocess
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from sqlalchemy.engine import make_url

_PG_BIN_DIR_ENV = "CIVICLENS_TEST_PG_BIN_DIR"
_DEFAULT_BIN_DIR = Path("C:/civiclens-test-postgres/pgsql/bin")


def _bin_dir() -> Path:
    configured = os.environ.get(_PG_BIN_DIR_ENV)
    return Path(configured) if configured else _DEFAULT_BIN_DIR


def full_postgres_available() -> bool:
    bin_dir = _bin_dir()
    return (bin_dir / "initdb.exe").exists() and (bin_dir / "pg_ctl.exe").exists()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class FullPostgresServer:
    def __init__(self, data_dir: Path, port: int, bin_dir: Path) -> None:
        self.data_dir = data_dir
        self.port = port
        self._bin_dir = bin_dir

    def get_uri(self) -> str:
        return f"postgresql://postgres@127.0.0.1:{self.port}/postgres"

    def cleanup(self) -> None:
        subprocess.run(
            [str(self._bin_dir / "pg_ctl"), "-D", str(self.data_dir), "-m", "fast", "stop"],
            check=False,
            capture_output=True,
        )
        shutil.rmtree(self.data_dir, ignore_errors=True)


def start_full_postgres(data_dir: Path) -> FullPostgresServer:
    """Initializes and starts a throwaway Postgres cluster with trust
    auth (test-only, never a real deployment target) on a free local
    port."""
    bin_dir = _bin_dir()
    port = _find_free_port()

    subprocess.run(
        [
            str(bin_dir / "initdb"),
            "-D",
            str(data_dir),
            "-U",
            "postgres",
            "--auth=trust",
            "-E",
            "UTF8",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    # NOT capture_output=True here: pg_ctl start's daemonized postgres.exe
    # child can inherit the parent's piped stdout/stderr handles on
    # Windows, so subprocess.run keeps waiting for those pipes to reach
    # EOF long after pg_ctl itself has exited and the server is actually
    # up — observed directly (a 280s+ hang) before switching to DEVNULL,
    # which sidesteps the inherited-handle problem entirely.
    log_path = data_dir / "server.log"
    subprocess.run(
        [
            str(bin_dir / "pg_ctl"),
            "-D",
            str(data_dir),
            "-l",
            str(log_path),
            "-o",
            f"-p {port} -c listen_addresses=127.0.0.1",
            "start",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(60):
        result = subprocess.run(
            [str(bin_dir / "pg_isready"), "-h", "127.0.0.1", "-p", str(port)],
            capture_output=True,
        )
        if result.returncode == 0:
            return FullPostgresServer(data_dir, port, bin_dir)
        time.sleep(0.5)

    raise RuntimeError("Full Postgres server did not become ready in time")


@contextmanager
def scratch_database(admin_database_url: str) -> Generator[str, None, None]:
    """Creates a throwaway database on the given server and yields its
    connection URL, dropping it afterward.

    Used by tests that need to run a full, destructive migration
    upgrade/downgrade/upgrade cycle without disturbing the
    session-scoped database other tests (`full_pg_database_url`,
    `migrated_engine`) are using concurrently — a fresh *database* on
    the shared server, rather than a whole second server process.
    """
    url = make_url(admin_database_url)
    db_name = f"civiclens_test_{uuid.uuid4().hex[:16]}"
    admin_dsn = url.set(database="postgres").render_as_string(hide_password=False)
    admin_dsn = admin_dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    scratch_url = url.set(database=db_name).render_as_string(hide_password=False)

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{db_name}"')
    try:
        yield scratch_url
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (db_name,),
            )
            conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
