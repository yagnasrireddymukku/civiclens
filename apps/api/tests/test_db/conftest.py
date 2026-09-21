from collections.abc import Generator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from alembic import command

ALEMBIC_INI_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


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
    plain SQLAlchemy engine pointed at the now-migrated database."""
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
