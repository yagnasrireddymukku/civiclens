"""Migration test for the jobs domain — needs a real Postgres (see
tests/conftest.py's `full_pg_database_url` fixture) since the migration
chain now unconditionally includes Phase 5's `CREATE EXTENSION pg_trgm`.

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

JOB_TABLES = {"organizations", "departments", "jobs", "job_notifications", "job_vacancies"}


def test_jobs_domain_migration_applies_and_reverses_cleanly(full_pg_database_url: str) -> None:
    with scratch_database(full_pg_database_url) as db_url:
        config = Config(str(ALEMBIC_INI_PATH))
        config.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(config, "head")

        engine = sa.create_engine(db_url, future=True)
        try:
            tables = set(sa.inspect(engine).get_table_names())
            assert JOB_TABLES <= tables
        finally:
            engine.dispose()

        # This migration is the current head, so "-1" isolates it
        # cleanly (unlike test_search/test_migrations.py, which has to
        # walk down past this migration now that it sits on top).
        command.downgrade(config, "-1")

        engine = sa.create_engine(db_url, future=True)
        try:
            inspector = sa.inspect(engine)
            tables = set(inspector.get_table_names())
            assert JOB_TABLES.isdisjoint(tables)
            assert "search_documents" in tables  # Phase 5's table untouched
            assert "states" in tables  # Phase 3's tables untouched

            # The known Alembic autogenerate gap (docs/DATABASE.md §7):
            # native Postgres ENUM types created alongside a column
            # aren't dropped by `op.drop_table` and must be dropped
            # explicitly, or a subsequent upgrade fails with "type
            # already exists". `verification_status` is reused from
            # Phase 3 (via `create_type=False`) and must survive.
            with engine.connect() as connection:
                enum_count = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_type WHERE typname IN "
                        "('organization_type', 'employment_type', "
                        "'job_publication_status', 'job_notification_status')"
                    )
                ).scalar()
                verification_status_still_exists = connection.execute(
                    sa.text("SELECT COUNT(*) FROM pg_type WHERE typname = 'verification_status'")
                ).scalar()
            assert enum_count == 0, "downgrade left orphaned jobs-domain enum types behind"
            assert verification_status_still_exists == 1
        finally:
            engine.dispose()

        # The real regression this guards: downgrade must leave the
        # database in a state where upgrading again succeeds.
        command.upgrade(config, "head")
        engine = sa.create_engine(db_url, future=True)
        try:
            assert JOB_TABLES <= set(sa.inspect(engine).get_table_names())
        finally:
            engine.dispose()
