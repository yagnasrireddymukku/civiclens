import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from alembic import command
from app.core.db.session import get_db
from app.main import app
from tests._full_pg_utils import full_postgres_available, start_full_postgres

_ENV_URL_VAR = "CIVICLENS_TEST_FULL_PG_URL"
ALEMBIC_INI_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    """A `TestClient` whose `get_db` dependency is overridden to yield
    the same transactional `db_session` fixture other tests use, so an
    API test's writes are visible within the request and rolled back at
    teardown like every other DB test — instead of a real request-scoped
    session hitting the app's actually-configured `DATABASE_URL`."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session")
def full_pg_database_url() -> Generator[str, None, None]:
    """A real PostgreSQL connection string with every contrib module
    (`pg_trgm` included) available.

    Required by every test that migrates a database to `head`: from
    Phase 5 onward the migration chain unconditionally runs
    `CREATE EXTENSION IF NOT EXISTS pg_trgm` (see tests/_full_pg_utils.py
    for why the previously-used `pgserver` no longer suffices on this
    environment). Shared by tests/test_db and tests/test_search so both
    packages resolve the same way: `CIVICLENS_TEST_FULL_PG_URL` (CI's
    `postgres:16` service container) first, else a local full-PostgreSQL
    binary distribution, else skip with a clear reason.
    """
    env_url = os.environ.get(_ENV_URL_VAR)
    if env_url:
        yield env_url
        return

    if not full_postgres_available():
        pytest.skip(
            f"No Postgres with pg_trgm available: set {_ENV_URL_VAR} "
            "(e.g. a postgres:16 service container) or install a full "
            "PostgreSQL distribution at the path tests/_full_pg_utils.py expects."
        )

    with tempfile.TemporaryDirectory(prefix="civiclens_test_pg_") as tmpdir:
        server = start_full_postgres(Path(tmpdir) / "pgdata")
        try:
            yield server.get_uri().replace("postgresql://", "postgresql+psycopg://", 1)
        finally:
            server.cleanup()


@pytest.fixture(scope="session")
def alembic_config(full_pg_database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", full_pg_database_url)
    return config


@pytest.fixture(scope="session")
def migrated_engine(
    alembic_config: Config, full_pg_database_url: str
) -> Generator[Engine, None, None]:
    """Runs every migration once per test session, then hands back a
    plain SQLAlchemy engine pointed at the now-migrated database. Shared
    by every test package (test_db, test_search, test_jobs, ...) — one
    migrated database and one engine per test session, not one per
    package."""
    command.upgrade(alembic_config, "head")
    engine = create_engine(full_pg_database_url, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(migrated_engine: Engine) -> Generator[Session, None, None]:
    """One transaction per test, rolled back at teardown — see
    docs/TESTING.md §3. Uses the SAVEPOINT pattern so ORM-level
    `session.commit()` calls inside the code under test don't end the
    outer, real transaction early.
    """
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
