"""Source management (read-only this phase): listing with version
counts, detail with version history, and a 404-safe missing-source
lookup — see `app.admin.service`'s module docstring for why no route
creates a `Source`/`SourceVersion` this phase.
"""

import datetime
import uuid

from sqlalchemy.orm import Session

from app.admin import service
from app.sources.models import SourceVersion
from tests.test_tracking._helpers import make_source


def test_list_sources_reports_version_counts(db_session: Session) -> None:
    source_with_versions = make_source(db_session, url="https://example-test.invalid/a")
    make_source(db_session, url="https://example-test.invalid/b")
    db_session.add(
        SourceVersion(
            source_id=source_with_versions.id,
            content_hash="abc123",
            captured_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        )
    )
    db_session.add(
        SourceVersion(
            source_id=source_with_versions.id,
            content_hash="def456",
            captured_at=datetime.datetime(2026, 2, 1, tzinfo=datetime.UTC),
        )
    )
    db_session.flush()

    result = service.list_sources(db_session)

    assert result.total_count == 2
    counts_by_id = {row.source.id: row.version_count for row in result.rows}
    assert counts_by_id[source_with_versions.id] == 2


def test_get_source_detail_includes_version_history(db_session: Session) -> None:
    source = make_source(db_session)
    db_session.add(
        SourceVersion(
            source_id=source.id,
            content_hash="abc123",
            captured_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        )
    )
    db_session.flush()

    detail = service.get_source_detail(db_session, source_id=source.id)

    assert detail is not None
    assert len(detail.versions) == 1
    assert detail.versions[0].content_hash == "abc123"


def test_get_source_detail_returns_none_for_a_nonexistent_source(db_session: Session) -> None:
    assert service.get_source_detail(db_session, source_id=uuid.uuid4()) is None
