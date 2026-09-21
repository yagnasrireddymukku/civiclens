"""Fixtures for search tests, which need `pg_trgm` — see
tests/_full_pg_utils.py and the shared `full_pg_database_url` fixture in
tests/conftest.py for why this can't reuse tests/test_db's old
pgserver-backed fixtures on this environment, and how a real Postgres
with pg_trgm is resolved (CI service container vs. local binary).
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from alembic import command

ALEMBIC_INI_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


@pytest.fixture(scope="session")
def search_alembic_config(full_pg_database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", full_pg_database_url)
    return config


@pytest.fixture(scope="session")
def search_migrated_engine(
    search_alembic_config: Config, full_pg_database_url: str
) -> Generator[Engine, None, None]:
    # No manual pg_trgm bootstrap here on purpose: the migration itself
    # runs `CREATE EXTENSION IF NOT EXISTS pg_trgm`, so running it
    # against a database that has never seen it before (as this always
    # is) is itself part of what this fixture verifies.
    command.upgrade(search_alembic_config, "head")
    engine = create_engine(full_pg_database_url, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def search_db_session(search_migrated_engine: Engine) -> Generator[Session, None, None]:
    connection = search_migrated_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
