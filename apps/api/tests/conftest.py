import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests._full_pg_utils import full_postgres_available, start_full_postgres

_ENV_URL_VAR = "CIVICLENS_TEST_FULL_PG_URL"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


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
