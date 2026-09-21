"""Migration test for search_documents — needs a real Postgres with
`pg_trgm` (see tests/_full_pg_utils.py and tests/conftest.py's
`full_pg_database_url` fixture) because the migration creates a
`gin_trgm_ops` index.

Runs against its own throwaway database (via `scratch_database`) rather
than the shared `search_migrated_engine` fixture, since this test's whole
point is a destructive upgrade/downgrade/upgrade cycle that would
interfere with every other test sharing that session-scoped database.
"""

import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from tests._full_pg_utils import scratch_database
from tests.test_search.conftest import ALEMBIC_INI_PATH


def test_search_documents_migration_applies_and_reverses_cleanly(
    full_pg_database_url: str,
) -> None:
    with scratch_database(full_pg_database_url) as db_url:
        # No manual pg_trgm bootstrap: the migration's own
        # `CREATE EXTENSION IF NOT EXISTS pg_trgm` must be what makes
        # this pass, against a database that has never seen it.
        config = Config(str(ALEMBIC_INI_PATH))
        config.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(config, "head")

        engine = sa.create_engine(db_url, future=True)
        try:
            inspector = sa.inspect(engine)
            assert "search_documents" in inspector.get_table_names()
            index_names = {index["name"] for index in inspector.get_indexes("search_documents")}
            assert "ix_search_documents_search_vector" in index_names
            assert "ix_search_documents_title_trgm" in index_names
        finally:
            engine.dispose()

        # Downgrade one revision (this migration only) and confirm
        # the table disappears without disturbing Phase 3's tables.
        command.downgrade(config, "-1")

        engine = sa.create_engine(db_url, future=True)
        try:
            inspector = sa.inspect(engine)
            tables = set(inspector.get_table_names())
            assert "search_documents" not in tables
            assert "states" in tables  # Phase 3 tables untouched
        finally:
            engine.dispose()

        # And upgrading again must succeed. This migration's
        # upgrade() re-declares the existing verification_status
        # enum (reused from Phase 3's migration, not a new type) —
        # SQLAlchemy's Postgres ENUM DDL does its own checkfirst
        # query against pg_type before ever emitting CREATE TYPE, so
        # this works without needing an explicit downgrade-side DROP
        # TYPE the way Phase 3's *new* enum types did (see that
        # migration's downgrade() for the contrasting case).
        command.upgrade(config, "head")
