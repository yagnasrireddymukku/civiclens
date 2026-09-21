"""Migration workflow test — docs/ROADMAP.md Phase 3 acceptance criterion:
"Migrations apply cleanly on a fresh DB and reverse cleanly."

Uses its own isolated Postgres instance/directory rather than the shared
`migrated_engine` fixture (which stays migrated for the whole session) —
this test's entire point is exercising the fresh-database upgrade and the
full downgrade, which would otherwise interfere with every other test in
this package.
"""

import tempfile

import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from tests.test_db._pg_utils import start_test_postgres, to_sqlalchemy_url
from tests.test_db.conftest import ALEMBIC_INI_PATH

EXPECTED_TABLES = {
    "states",
    "districts",
    "constituencies",
    "sources",
    "source_versions",
    "verification_records",
    "change_records",
    "users",
    "profiles",
    "alembic_version",
}


def test_fresh_database_migrates_up_and_down_cleanly() -> None:
    with tempfile.TemporaryDirectory(prefix="civiclens_migration_test_pg_") as pgdir:
        server = start_test_postgres(pgdir)
        try:
            db_url = to_sqlalchemy_url(server.get_uri())
            config = Config(str(ALEMBIC_INI_PATH))
            config.set_main_option("sqlalchemy.url", db_url)

            command.upgrade(config, "head")

            engine = sa.create_engine(db_url, future=True)
            try:
                inspector = sa.inspect(engine)
                assert EXPECTED_TABLES <= set(inspector.get_table_names())
            finally:
                engine.dispose()

            command.downgrade(config, "base")

            engine = sa.create_engine(db_url, future=True)
            try:
                inspector = sa.inspect(engine)
                remaining = set(inspector.get_table_names()) - {"alembic_version"}
                assert remaining == set(), f"downgrade left tables behind: {remaining}"

                # The known Alembic autogenerate gap this migration works
                # around: native Postgres ENUM types are not dropped by
                # `op.drop_table` and must be dropped explicitly in
                # downgrade(), or a subsequent upgrade fails with
                # "type already exists".
                with engine.connect() as connection:
                    enum_count = connection.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM pg_type WHERE typname IN "
                            "('state_status', 'constituency_type', 'verification_status', "
                            "'change_review_status', 'user_role')"
                        )
                    ).scalar()
                assert enum_count == 0, "downgrade left orphaned enum types behind"
            finally:
                engine.dispose()

            # The real regression this guards: downgrade must leave the
            # database in a state where upgrading again succeeds.
            command.upgrade(config, "head")
            engine = sa.create_engine(db_url, future=True)
            try:
                inspector = sa.inspect(engine)
                assert EXPECTED_TABLES <= set(inspector.get_table_names())
            finally:
                engine.dispose()
        finally:
            server.cleanup()
