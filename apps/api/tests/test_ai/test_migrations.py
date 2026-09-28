"""Migration test for `ai_knowledge_chunks` — needs a real Postgres (see
tests/conftest.py's `full_pg_database_url` fixture). Runs against its own
throwaway database via `scratch_database`, mirroring
tests/test_documents/test_migrations.py's pattern.
"""

import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from tests._full_pg_utils import scratch_database
from tests.conftest import ALEMBIC_INI_PATH

AI_TABLES = {"ai_knowledge_chunks"}


def test_ai_knowledge_chunks_migration_applies_and_reverses_cleanly(
    full_pg_database_url: str,
) -> None:
    with scratch_database(full_pg_database_url) as db_url:
        config = Config(str(ALEMBIC_INI_PATH))
        config.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(config, "head")

        engine = sa.create_engine(db_url, future=True)
        try:
            tables = set(sa.inspect(engine).get_table_names())
            assert AI_TABLES <= tables
            columns = {c["name"] for c in sa.inspect(engine).get_columns("ai_knowledge_chunks")}
            assert {"entity_type", "entity_id", "locale", "chunk_index", "embedding"} <= columns
        finally:
            engine.dispose()

        # No longer the current head (the auth/tracking/notifications
        # migration, Tracking + Notifications rescheduled from Phase 12,
        # now sits on top), so a single "-1" no longer isolates this
        # migration — walk down one revision at a time, mirroring
        # tests/test_documents/test_migrations.py's identical pattern.
        for _ in range(2):
            command.downgrade(config, "-1")
            engine = sa.create_engine(db_url, future=True)
            try:
                tables = set(sa.inspect(engine).get_table_names())
            finally:
                engine.dispose()
            if AI_TABLES.isdisjoint(tables):
                break
        else:
            raise AssertionError("ai_knowledge_chunks was still present after 2 downgrades")

        engine = sa.create_engine(db_url, future=True)
        try:
            tables = set(sa.inspect(engine).get_table_names())
            assert AI_TABLES.isdisjoint(tables)
            assert "search_documents" in tables  # Phase 5's tables untouched
            assert "eligibility_rules" in tables  # Phase 11's tables untouched
        finally:
            engine.dispose()

        # The real regression this guards: downgrade must leave the
        # database in a state where upgrading again succeeds.
        command.upgrade(config, "head")
        engine = sa.create_engine(db_url, future=True)
        try:
            assert AI_TABLES <= set(sa.inspect(engine).get_table_names())
        finally:
            engine.dispose()
