"""Migration test for the combined auth/tracking/notifications
migration (Tracking + Notifications, rescheduled from Phase 12) —
needs a real Postgres (see tests/conftest.py's
`full_pg_database_url` fixture). Runs against its own throwaway
database via `scratch_database`, mirroring
tests/test_documents/test_migrations.py's pattern. All five additions
(the `users.email_notifications_enabled` column, `refresh_tokens`,
`tracked_items`, `notifications`, `notification_delivery_attempts`) are
one Alembic revision, so one test covers all of them together.
"""

import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from tests._full_pg_utils import scratch_database
from tests.conftest import ALEMBIC_INI_PATH

NEW_TABLES = {"refresh_tokens", "tracked_items", "notifications", "notification_delivery_attempts"}


def test_auth_tracking_notifications_migration_applies_and_reverses_cleanly(
    full_pg_database_url: str,
) -> None:
    with scratch_database(full_pg_database_url) as db_url:
        config = Config(str(ALEMBIC_INI_PATH))
        config.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(config, "head")

        engine = sa.create_engine(db_url, future=True)
        try:
            tables = set(sa.inspect(engine).get_table_names())
            assert NEW_TABLES <= tables
            user_columns = {c["name"] for c in sa.inspect(engine).get_columns("users")}
            assert "email_notifications_enabled" in user_columns
        finally:
            engine.dispose()

        # This migration is the current head, so "-1" isolates it
        # cleanly — no later phase's migration sits on top of it yet.
        command.downgrade(config, "-1")

        engine = sa.create_engine(db_url, future=True)
        try:
            inspector = sa.inspect(engine)
            tables = set(inspector.get_table_names())
            assert NEW_TABLES.isdisjoint(tables)
            user_columns = {c["name"] for c in inspector.get_columns("users")}
            assert "email_notifications_enabled" not in user_columns
            assert "jobs" in tables  # Phase 6's tables untouched
            assert "ai_knowledge_chunks" in tables  # Phase 12's tables untouched

            with engine.connect() as connection:
                new_enum_count = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_type WHERE typname IN "
                        "('notification_type', 'delivery_channel', 'delivery_status')"
                    )
                ).scalar()
            assert new_enum_count == 0, "downgrade left orphaned notification enum types behind"
        finally:
            engine.dispose()

        # The real regression this guards: downgrade must leave the
        # database in a state where upgrading again succeeds.
        command.upgrade(config, "head")
        engine = sa.create_engine(db_url, future=True)
        try:
            assert NEW_TABLES <= set(sa.inspect(engine).get_table_names())
        finally:
            engine.dispose()
