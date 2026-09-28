"""Shared fixture-building helpers for tracking tests — reuses the same
shared-geography/organization/source helpers every other domain's test
suite already established (`tests.test_documents._helpers`).
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.sources.enums import ChangeReviewStatus
from app.sources.models import ChangeRecord, Source
from app.tracking.enums import TrackedEntityType
from app.tracking.models import TrackedItem


def make_tracked_item(
    session: Session,
    *,
    user_id: uuid.UUID,
    entity_type: TrackedEntityType,
    entity_id: uuid.UUID,
    **overrides: Any,
) -> TrackedItem:
    column_name = f"{entity_type.value}_id"
    defaults: dict[str, Any] = {
        "user_id": user_id,
        column_name: entity_id,
        "is_active": True,
    }
    defaults.update(overrides)
    item = TrackedItem(**defaults)
    session.add(item)
    session.flush()
    return item


def make_change_record(
    session: Session,
    *,
    entity_type: TrackedEntityType,
    entity_id: uuid.UUID,
    field: str,
    old_value: str | None,
    new_value: str | None,
    review_status: ChangeReviewStatus = ChangeReviewStatus.PENDING,
    **overrides: Any,
) -> ChangeRecord:
    defaults: dict[str, Any] = dict(
        entity_type=entity_type.value,
        entity_id=entity_id,
        field=field,
        old_value=old_value,
        new_value=new_value,
        detected_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
        review_status=review_status,
    )
    defaults.update(overrides)
    record = ChangeRecord(**defaults)
    session.add(record)
    session.flush()
    return record


def make_source(session: Session, **overrides: Any) -> Source:
    defaults: dict[str, Any] = dict(
        url="https://example-test.invalid/notice/tracking",
        title="Test Notice — Not Real",
        organization="Test Recruitment Board — Not Real",
        source_type="test-fixture",
        retrieved_date=datetime.date(2026, 1, 1),
    )
    defaults.update(overrides)
    source = Source(**defaults)
    session.add(source)
    session.flush()
    return source
