"""Migration test for the schemes domain — needs a real Postgres (see
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

SCHEME_TABLES = {
    "schemes",
    "scheme_benefits",
    "scheme_requirements",
    "scheme_required_documents",
    "scheme_application_methods",
    "scheme_related_services",
}


def test_schemes_domain_migration_applies_and_reverses_cleanly(
    full_pg_database_url: str,
) -> None:
    with scratch_database(full_pg_database_url) as db_url:
        config = Config(str(ALEMBIC_INI_PATH))
        config.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(config, "head")

        engine = sa.create_engine(db_url, future=True)
        try:
            tables = set(sa.inspect(engine).get_table_names())
            assert SCHEME_TABLES <= tables
        finally:
            engine.dispose()

        # Downgrade past whatever now sits on top of this migration in
        # the chain (Phase 9's scholarship_details, as of this writing)
        # one revision at a time, until the scheme tables themselves are
        # gone — mirrors tests/test_jobs/test_migrations.py's identical
        # walk-down, needed for the same reason: "-1" alone no longer
        # isolates this migration once a later phase adds its own on top.
        for _ in range(8):
            command.downgrade(config, "-1")
            engine = sa.create_engine(db_url, future=True)
            try:
                tables = set(sa.inspect(engine).get_table_names())
            finally:
                engine.dispose()
            if SCHEME_TABLES.isdisjoint(tables):
                break
        else:
            raise AssertionError("scheme tables were still present after 8 downgrades")

        engine = sa.create_engine(db_url, future=True)
        try:
            inspector = sa.inspect(engine)
            tables = set(inspector.get_table_names())
            assert SCHEME_TABLES.isdisjoint(tables)
            assert "services" in tables  # Phase 7's tables untouched
            assert "jobs" in tables  # Phase 6's tables untouched
            assert "states" in tables  # Phase 3's tables untouched

            # The known Alembic autogenerate gap (docs/DATABASE.md §7):
            # native Postgres ENUM types created alongside a column
            # aren't dropped by `op.drop_table` and must be dropped
            # explicitly, or a subsequent upgrade fails with "type
            # already exists". `requirement_type`/
            # `application_channel_type` are reused from Phase 7 (via
            # `create_type=False`) and must survive, since
            # `service_requirements`/`service_application_methods`
            # still reference them.
            with engine.connect() as connection:
                enum_count = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_type WHERE typname IN "
                        "('scheme_category', 'scheme_publication_status', 'benefit_type')"
                    )
                ).scalar()
                reused_still_exist = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_type WHERE typname IN "
                        "('requirement_type', 'application_channel_type', "
                        "'verification_status')"
                    )
                ).scalar()
            assert enum_count == 0, "downgrade left orphaned scheme-domain enum types behind"
            assert reused_still_exist == 3
        finally:
            engine.dispose()

        # The real regression this guards: downgrade must leave the
        # database in a state where upgrading again succeeds.
        command.upgrade(config, "head")
        engine = sa.create_engine(db_url, future=True)
        try:
            assert SCHEME_TABLES <= set(sa.inspect(engine).get_table_names())
        finally:
            engine.dispose()
