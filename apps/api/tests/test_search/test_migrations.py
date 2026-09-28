"""Migration test for search_documents — needs a real Postgres with
`pg_trgm` (see tests/_full_pg_utils.py and tests/conftest.py's
`full_pg_database_url` fixture) because the migration creates a
`gin_trgm_ops` index.

Runs against its own throwaway database (via `scratch_database`) rather
than the shared `migrated_engine` fixture, since this test's whole point
is a destructive upgrade/downgrade/upgrade cycle that would interfere
with every other test sharing that session-scoped database.
"""

import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from tests._full_pg_utils import scratch_database
from tests.conftest import ALEMBIC_INI_PATH


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

        # Downgrade past whatever now sits on top of this migration in
        # the chain (Phase 10's documents domain, as of this writing) one
        # revision at a time, until search_documents itself is gone —
        # "-1" alone no longer isolates this migration once a later
        # phase adds its own migration on top, so this walks down
        # instead of assuming a fixed distance from head. Bounded so a
        # real bug (the table never disappearing) fails loudly instead
        # of downgrading all the way to base. The bound has grown by one
        # each phase that added a migration on top (5 -> 6 in Phase 10);
        # it is a distance-from-head count, not a fundamental limit, and
        # is expected to keep growing.
        for _ in range(8):
            command.downgrade(config, "-1")
            engine = sa.create_engine(db_url, future=True)
            try:
                tables = set(sa.inspect(engine).get_table_names())
            finally:
                engine.dispose()
            if "search_documents" not in tables:
                break
        else:
            raise AssertionError("search_documents was still present after 8 downgrades")

        assert "states" in tables  # Phase 3 tables untouched

        # And upgrading again must succeed. This migration's
        # upgrade() re-declares the existing verification_status
        # enum (reused from Phase 3's migration, not a new type) —
        # SQLAlchemy's Postgres ENUM DDL does its own checkfirst
        # query against pg_type before ever emitting CREATE TYPE, so
        # this works without needing an explicit downgrade-side DROP
        # TYPE the way Phase 3's *new* enum types did (see that
        # migration's downgrade() for the contrasting case).
        command.upgrade(config, "head")
