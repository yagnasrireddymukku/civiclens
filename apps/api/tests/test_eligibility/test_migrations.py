"""Migration test for the eligibility domain — needs a real Postgres (see
tests/conftest.py's `full_pg_database_url` fixture). Runs against its own
throwaway database via `scratch_database`, mirroring
tests/test_documents/test_migrations.py exactly.
"""

import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from tests._full_pg_utils import scratch_database
from tests.conftest import ALEMBIC_INI_PATH

ELIGIBILITY_TABLES = {"eligibility_rules", "eligibility_conditions"}


def test_eligibility_domain_migration_applies_and_reverses_cleanly(
    full_pg_database_url: str,
) -> None:
    with scratch_database(full_pg_database_url) as db_url:
        config = Config(str(ALEMBIC_INI_PATH))
        config.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(config, "head")

        engine = sa.create_engine(db_url, future=True)
        try:
            tables = set(sa.inspect(engine).get_table_names())
            assert ELIGIBILITY_TABLES <= tables
        finally:
            engine.dispose()

        # No longer the current head (Phase 12's ai_knowledge_chunks
        # migration now sits on top), so a single "-1" no longer
        # isolates this migration — walk down one revision at a time,
        # mirroring tests/test_documents/test_migrations.py's identical
        # pattern.
        for _ in range(3):
            command.downgrade(config, "-1")
            engine = sa.create_engine(db_url, future=True)
            try:
                tables = set(sa.inspect(engine).get_table_names())
            finally:
                engine.dispose()
            if ELIGIBILITY_TABLES.isdisjoint(tables):
                break
        else:
            raise AssertionError("eligibility tables were still present after 3 downgrades")

        engine = sa.create_engine(db_url, future=True)
        try:
            inspector = sa.inspect(engine)
            tables = set(inspector.get_table_names())
            assert ELIGIBILITY_TABLES.isdisjoint(tables)
            assert "jobs" in tables  # Phase 6's tables untouched
            assert "schemes" in tables  # Phase 8's tables untouched
            assert "services" in tables  # Phase 7's tables untouched

            # The known Alembic autogenerate gap (docs/DATABASE.md §7):
            # native Postgres ENUM types created alongside a column
            # aren't dropped by `op.drop_table` and must be dropped
            # explicitly. `verification_status` is reused (via
            # `create_type=False`) and must survive, since jobs/schemes/
            # services still reference it.
            with engine.connect() as connection:
                new_enum_count = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_type WHERE typname IN "
                        "('eligibility_attribute', 'eligibility_operator', "
                        "'eligibility_rule_publication_status')"
                    )
                ).scalar()
                reused_still_exists = connection.execute(
                    sa.text("SELECT COUNT(*) FROM pg_type WHERE typname = 'verification_status'")
                ).scalar()
            assert new_enum_count == 0, "downgrade left orphaned eligibility enum types behind"
            assert reused_still_exists == 1
        finally:
            engine.dispose()

        # The real regression this guards: downgrade must leave the
        # database in a state where upgrading again succeeds.
        command.upgrade(config, "head")
        engine = sa.create_engine(db_url, future=True)
        try:
            assert ELIGIBILITY_TABLES <= set(sa.inspect(engine).get_table_names())
        finally:
            engine.dispose()
