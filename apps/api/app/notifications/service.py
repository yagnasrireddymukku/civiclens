"""Notification inbox logic — creation (idempotent by dedup key),
listing, and read-state. The only module that writes `notifications`
directly. `EMAIL` delivery attempts are written by
`app.notifications.delivery` (bounded, retried); the `IN_APP` attempt is
written right here, as `SENT`, at creation time — writing the
`Notification` row *is* in-app delivery, so there is nothing to persist
separately or retry for that channel.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.notifications.enums import DeliveryChannel, DeliveryStatus, NotificationType
from app.notifications.models import Notification, NotificationDeliveryAttempt


class NotificationNotFoundError(Exception):
    """ "Doesn't exist" or "belongs to another user" — never
    distinguished to the caller (same IDOR-safe convention as
    `app.tracking.service.TrackedItemNotFoundError`)."""


def create_notification(
    session: Session,
    *,
    user_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
    dedup_key: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    source_id: uuid.UUID | None = None,
    change_record_id: uuid.UUID | None = None,
) -> Notification | None:
    """`None` when a notification with this exact `(user_id, dedup_key)`
    already exists — the insert is silently skipped (`ON CONFLICT DO
    NOTHING`), not an error, so a sweep that runs twice (or is retried
    after a partial failure) never creates a duplicate. The database
    constraint (`uq_notifications_user_dedup_key`) is the actual
    guarantee; this `ON CONFLICT` clause is what makes relying on it
    safe to call repeatedly rather than a crash."""

    stmt = (
        pg_insert(Notification)
        .values(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            dedup_key=dedup_key,
            entity_type=entity_type,
            entity_id=entity_id,
            source_id=source_id,
            change_record_id=change_record_id,
        )
        .on_conflict_do_nothing(constraint="uq_notifications_user_dedup_key")
        .returning(Notification)
    )
    result = session.execute(stmt).scalar_one_or_none()
    if result is not None:
        session.add(
            NotificationDeliveryAttempt(
                notification_id=result.id,
                channel=DeliveryChannel.IN_APP,
                status=DeliveryStatus.SENT,
                attempt_number=1,
                attempted_at=datetime.now(UTC),
            )
        )
        session.flush()
    return result


@dataclass(frozen=True, slots=True)
class NotificationListResult:
    rows: list[Notification]
    total_count: int
    unread_count: int


def list_notifications(
    session: Session, *, user_id: uuid.UUID, page: int = 1, page_size: int = 20
) -> NotificationListResult:
    base = select(Notification).where(Notification.user_id == user_id)
    total_count = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    unread_count = (
        session.scalar(
            select(func.count()).select_from(base.where(Notification.read_at.is_(None)).subquery())
        )
        or 0
    )
    rows = (
        session.execute(
            base.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return NotificationListResult(
        rows=list(rows), total_count=total_count, unread_count=unread_count
    )


def _get_owned(session: Session, *, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    notification = session.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        raise NotificationNotFoundError(notification_id)
    return notification


def mark_read(session: Session, *, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    notification = _get_owned(session, user_id=user_id, notification_id=notification_id)
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
    return notification


def mark_all_read(session: Session, *, user_id: uuid.UUID) -> int:
    now = datetime.now(UTC)
    unread_filter = (Notification.user_id == user_id) & Notification.read_at.is_(None)
    unread_count = session.scalar(select(func.count()).where(unread_filter)) or 0
    session.execute(update(Notification).where(unread_filter).values(read_at=now))
    return unread_count
