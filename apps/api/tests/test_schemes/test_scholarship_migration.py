"""Migration test for `scholarship_details` (Phase 9) — needs a real
Postgres (see tests/conftest.py's `full_pg_database_url` fixture) since
the migration chain now unconditionally includes Phase 5's `CREATE
EXTENSION pg_trgm`.

Runs against its own throwaway database (via `scratch_database`) rather
than the shared `migrated_engine` fixture, since this test's whole point
is a destructive upgrade/downgrade/upgrade cycle that would interfere
with every other test sharing that session-scoped database. Mirrors
tests/test_schemes/test_migrations.py's pattern exactly.
"""

import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from tests._full_pg_utils import scratch_database
from tests.conftest import ALEMBIC_INI_PATH


def test_scholarship_details_migration_applies_and_reverses_cleanly(
    full_pg_database_url: str,
) -> None:
    with scratch_database(full_pg_database_url) as db_url:
        config = Config(str(ALEMBIC_INI_PATH))
        config.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(config, "head")

        engine = sa.create_engine(db_url, future=True)
        try:
            tables = set(sa.inspect(engine).get_table_names())
            assert "scholarship_details" in tables
        finally:
            engine.dispose()

        # Downgrade past whatever now sits on top of this migration in
        # the chain (Phase 10's documents domain, as of this writing)
        # one revision at a time, until scholarship_details itself is
        # gone — mirrors tests/test_jobs/test_migrations.py's identical
        # walk-down, needed for the same reason: "-1" alone no longer
        # isolates this migration once a later phase adds its own on
        # top.
        for _ in range(8):
            command.downgrade(config, "-1")
            engine = sa.create_engine(db_url, future=True)
            try:
                tables = set(sa.inspect(engine).get_table_names())
            finally:
                engine.dispose()
            if "scholarship_details" not in tables:
                break
        else:
            raise AssertionError("scholarship_details was still present after 8 downgrades")

        engine = sa.create_engine(db_url, future=True)
        try:
            inspector = sa.inspect(engine)
            tables = set(inspector.get_table_names())
            assert "scholarship_details" not in tables
            assert "schemes" in tables  # Phase 8's tables untouched

            # The known Alembic autogenerate gap (docs/DATABASE.md §7):
            # native Postgres ENUM types created alongside a column
            # aren't dropped by `op.drop_table` and must be dropped
            # explicitly, or a subsequent upgrade fails with "type
            # already exists". `education_level`/`study_mode` are new
            # to this migration and must be dropped; `scheme_category`/
            # `benefit_type`/`scheme_publication_status` belong to
            # Phase 8's migration and must survive since `schemes`
            # still references them.
            with engine.connect() as connection:
                enum_count = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_type WHERE typname IN "
                        "('education_level', 'study_mode')"
                    )
                ).scalar()
                scheme_enums_still_exist = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_type WHERE typname IN "
                        "('scheme_category', 'benefit_type', 'scheme_publication_status')"
                    )
                ).scalar()
            assert enum_count == 0, "downgrade left orphaned education_level/study_mode behind"
            assert scheme_enums_still_exist == 3
        finally:
            engine.dispose()

        # The real regression this guards: downgrade must leave the
        # database in a state where upgrading again succeeds.
        command.upgrade(config, "head")
        engine = sa.create_engine(db_url, future=True)
        try:
            assert "scholarship_details" in set(sa.inspect(engine).get_table_names())
        finally:
            engine.dispose()
