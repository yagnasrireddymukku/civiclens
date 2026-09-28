"""Shared fixture-building helpers for notification tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.notifications.enums import NotificationType
from app.notifications.models import Notification


def make_notification(session: Session, *, user_id: uuid.UUID, **overrides: Any) -> Notification:
    defaults: dict[str, Any] = dict(
        user_id=user_id,
        notification_type=NotificationType.CHANGE_DETECTED,
        title="Test notification (Fixture)",
        body="A fictional notification body used only to exercise the notifications domain.",
        dedup_key=f"TEST:{uuid.uuid4()}",
        entity_type=None,
        entity_id=None,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    notification = Notification(**defaults)
    session.add(notification)
    session.flush()
    return notification
