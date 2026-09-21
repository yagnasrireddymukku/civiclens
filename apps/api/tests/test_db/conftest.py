import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from alembic import command
from tests.test_db._pg_utils import start_test_postgres, to_sqlalchemy_url

ALEMBIC_INI_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


@pytest.fixture(scope="session")
def pg_instance():
    """One real Postgres server for the whole test session — see
    tests/test_db/_pg_utils.py for why `pgserver` instead of Docker."""
    with tempfile.TemporaryDirectory(prefix="civiclens_test_pg_") as tmpdir:
        server = start_test_postgres(tmpdir)
        try:
            yield server
        finally:
            server.cleanup()


@pytest.fixture(scope="session")
def test_database_url(pg_instance) -> str:
    return to_sqlalchemy_url(pg_instance.get_uri())


@pytest.fixture(scope="session")
def alembic_config(test_database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", test_database_url)
    return config


@pytest.fixture(scope="session")
def migrated_engine(
    alembic_config: Config, test_database_url: str
) -> Generator[Engine, None, None]:
    """Runs every migration once per test session, then hands back a
    plain SQLAlchemy engine pointed at the now-migrated database."""
    command.upgrade(alembic_config, "head")
    engine = create_engine(test_database_url, future=True)
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
