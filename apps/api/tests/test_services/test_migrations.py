"""Migration test for the services domain — needs a real Postgres (see
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

SERVICE_TABLES = {
    "services",
    "service_requirements",
    "service_required_documents",
    "service_application_methods",
}


def test_services_domain_migration_applies_and_reverses_cleanly(
    full_pg_database_url: str,
) -> None:
    with scratch_database(full_pg_database_url) as db_url:
        config = Config(str(ALEMBIC_INI_PATH))
        config.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(config, "head")

        engine = sa.create_engine(db_url, future=True)
        try:
            tables = set(sa.inspect(engine).get_table_names())
            assert SERVICE_TABLES <= tables
        finally:
            engine.dispose()

        # Downgrade past whatever now sits on top of this migration in
        # the chain (Phase 8's schemes domain, as of this writing) one
        # revision at a time, until the service tables themselves are
        # gone — mirrors tests/test_jobs/test_migrations.py's identical
        # walk-down, needed for the same reason: "-1" alone no longer
        # isolates this migration once a later phase adds its own on top.
        for _ in range(7):
            command.downgrade(config, "-1")
            engine = sa.create_engine(db_url, future=True)
            try:
                tables = set(sa.inspect(engine).get_table_names())
            finally:
                engine.dispose()
            if SERVICE_TABLES.isdisjoint(tables):
                break
        else:
            raise AssertionError("service tables were still present after 7 downgrades")

        engine = sa.create_engine(db_url, future=True)
        try:
            inspector = sa.inspect(engine)
            tables = set(inspector.get_table_names())
            assert SERVICE_TABLES.isdisjoint(tables)
            assert "jobs" in tables  # Phase 6's tables untouched
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
                        "('service_category', 'delivery_mode', "
                        "'service_publication_status', 'requirement_type', "
                        "'application_channel_type')"
                    )
                ).scalar()
                verification_status_still_exists = connection.execute(
                    sa.text("SELECT COUNT(*) FROM pg_type WHERE typname = 'verification_status'")
                ).scalar()
                # organization_type is Phase 6's enum (app.institutions),
                # not this migration's — must survive too, since
                # organizations/departments still exist.
                organization_type_still_exists = connection.execute(
                    sa.text("SELECT COUNT(*) FROM pg_type WHERE typname = 'organization_type'")
                ).scalar()
            assert enum_count == 0, "downgrade left orphaned services-domain enum types behind"
            assert verification_status_still_exists == 1
            assert organization_type_still_exists == 1
        finally:
            engine.dispose()

        # The real regression this guards: downgrade must leave the
        # database in a state where upgrading again succeeds.
        command.upgrade(config, "head")
        engine = sa.create_engine(db_url, future=True)
        try:
            assert SERVICE_TABLES <= set(sa.inspect(engine).get_table_names())
        finally:
            engine.dispose()
