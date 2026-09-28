"""Migration test for the documents domain — needs a real Postgres (see
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

DOCUMENT_TABLES = {
    "civic_documents",
    "document_requirements",
    "document_supporting_documents",
    "document_application_methods",
}


def test_documents_domain_migration_applies_and_reverses_cleanly(
    full_pg_database_url: str,
) -> None:
    with scratch_database(full_pg_database_url) as db_url:
        config = Config(str(ALEMBIC_INI_PATH))
        config.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(config, "head")

        engine = sa.create_engine(db_url, future=True)
        try:
            tables = set(sa.inspect(engine).get_table_names())
            assert DOCUMENT_TABLES <= tables
            # The additive columns on already-shipped tables (this
            # phase's §14/§22 reverse-relationship groundwork).
            service_cols = {
                c["name"] for c in sa.inspect(engine).get_columns("service_required_documents")
            }
            scheme_cols = {
                c["name"] for c in sa.inspect(engine).get_columns("scheme_required_documents")
            }
            assert "civic_document_id" in service_cols
            assert "civic_document_id" in scheme_cols
        finally:
            engine.dispose()

        # No longer the current head (Phase 11's eligibility migration
        # now sits on top), so a single "-1" no longer isolates this
        # migration — walk down one revision at a time until the
        # document tables are gone, mirroring
        # tests/test_jobs/test_migrations.py's identical pattern.
        for _ in range(3):
            command.downgrade(config, "-1")
            engine = sa.create_engine(db_url, future=True)
            try:
                tables = set(sa.inspect(engine).get_table_names())
            finally:
                engine.dispose()
            if DOCUMENT_TABLES.isdisjoint(tables):
                break
        else:
            raise AssertionError("document tables were still present after 3 downgrades")

        engine = sa.create_engine(db_url, future=True)
        try:
            inspector = sa.inspect(engine)
            tables = set(inspector.get_table_names())
            assert DOCUMENT_TABLES.isdisjoint(tables)
            assert "schemes" in tables  # Phase 8/9's tables untouched
            assert "services" in tables  # Phase 7's tables untouched

            # The additive columns must roll back cleanly too — the
            # tables they were added to keep existing, just without the
            # column.
            service_cols = {c["name"] for c in inspector.get_columns("service_required_documents")}
            scheme_cols = {c["name"] for c in inspector.get_columns("scheme_required_documents")}
            assert "civic_document_id" not in service_cols
            assert "civic_document_id" not in scheme_cols

            # The known Alembic autogenerate gap (docs/DATABASE.md §7):
            # native Postgres ENUM types created alongside a column
            # aren't dropped by `op.drop_table` and must be dropped
            # explicitly, or a subsequent upgrade fails with "type
            # already exists". `delivery_mode`/`verification_status`/
            # `application_channel_type`/`requirement_type` are reused
            # from earlier phases (via `create_type=False`) and must
            # survive, since `services`/`schemes` still reference them.
            with engine.connect() as connection:
                new_enum_count = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_type WHERE typname IN "
                        "('document_type', 'document_category', "
                        "'document_publication_status')"
                    )
                ).scalar()
                reused_still_exist = connection.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_type WHERE typname IN "
                        "('delivery_mode', 'verification_status', "
                        "'application_channel_type', 'requirement_type')"
                    )
                ).scalar()
            assert new_enum_count == 0, "downgrade left orphaned document-domain enum types behind"
            assert reused_still_exist == 4
        finally:
            engine.dispose()

        # The real regression this guards: downgrade must leave the
        # database in a state where upgrading again succeeds.
        command.upgrade(config, "head")
        engine = sa.create_engine(db_url, future=True)
        try:
            assert DOCUMENT_TABLES <= set(sa.inspect(engine).get_table_names())
        finally:
            engine.dispose()
