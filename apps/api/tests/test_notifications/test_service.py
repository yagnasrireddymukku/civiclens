"""Notification inbox service tests: idempotent creation (dedup key),
the automatic `IN_APP` delivery attempt, listing/pagination/unread
count, read-state, and ownership.
"""

import datetime
import uuid

import pytest
from sqlalchemy.orm import Session

from app.notifications import service
from app.notifications.enums import DeliveryChannel, DeliveryStatus, NotificationType
from app.notifications.models import Notification
from tests.test_auth._helpers import make_user
from tests.test_notifications._helpers import make_notification


def test_create_notification_records_an_in_app_delivery_attempt(db_session: Session) -> None:
    user = make_user(db_session)
    notification = service.create_notification(
        db_session,
        user_id=user.id,
        notification_type=NotificationType.DEADLINE_REMINDER,
        title="Title",
        body="Body",
        dedup_key="KEY-1",
    )
    assert notification is not None
    assert len(notification.delivery_attempts) == 1
    attempt = notification.delivery_attempts[0]
    assert attempt.channel == DeliveryChannel.IN_APP
    assert attempt.status == DeliveryStatus.SENT


def test_create_notification_with_a_duplicate_dedup_key_returns_none(db_session: Session) -> None:
    user = make_user(db_session)
    first = service.create_notification(
        db_session,
        user_id=user.id,
        notification_type=NotificationType.DEADLINE_REMINDER,
        title="Title",
        body="Body",
        dedup_key="KEY-2",
    )
    second = service.create_notification(
        db_session,
        user_id=user.id,
        notification_type=NotificationType.DEADLINE_REMINDER,
        title="A different title, same event",
        body="A different body, same event",
        dedup_key="KEY-2",
    )
    assert first is not None
    assert second is None
    count = db_session.query(Notification).filter_by(user_id=user.id, dedup_key="KEY-2").count()
    assert count == 1


def test_list_notifications_orders_newest_first_and_reports_unread_count(
    db_session: Session,
) -> None:
    user = make_user(db_session)
    make_notification(
        db_session,
        user_id=user.id,
        dedup_key="A",
        created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    make_notification(
        db_session,
        user_id=user.id,
        dedup_key="B",
        created_at=datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC),
    )

    result = service.list_notifications(db_session, user_id=user.id)
    assert [n.dedup_key for n in result.rows] == ["B", "A"]
    assert result.total_count == 2
    assert result.unread_count == 2


def test_list_notifications_pagination(db_session: Session) -> None:
    user = make_user(db_session)
    for i in range(5):
        make_notification(db_session, user_id=user.id, dedup_key=f"KEY-{i}")

    page_one = service.list_notifications(db_session, user_id=user.id, page=1, page_size=2)
    assert len(page_one.rows) == 2
    assert page_one.total_count == 5


def test_mark_read_sets_read_at_and_reduces_unread_count(db_session: Session) -> None:
    user = make_user(db_session)
    notification = make_notification(db_session, user_id=user.id)

    service.mark_read(db_session, user_id=user.id, notification_id=notification.id)
    db_session.flush()

    assert notification.read_at is not None
    result = service.list_notifications(db_session, user_id=user.id)
    assert result.unread_count == 0


def test_mark_read_is_idempotent(db_session: Session) -> None:
    user = make_user(db_session)
    notification = make_notification(db_session, user_id=user.id)

    service.mark_read(db_session, user_id=user.id, notification_id=notification.id)
    first_read_at = notification.read_at
    service.mark_read(db_session, user_id=user.id, notification_id=notification.id)

    assert notification.read_at == first_read_at


def test_mark_read_rejects_another_users_notification(db_session: Session) -> None:
    owner = make_user(db_session)
    attacker = make_user(db_session)
    notification = make_notification(db_session, user_id=owner.id)

    with pytest.raises(service.NotificationNotFoundError):
        service.mark_read(db_session, user_id=attacker.id, notification_id=notification.id)


def test_mark_read_rejects_a_nonexistent_notification(db_session: Session) -> None:
    user = make_user(db_session)
    with pytest.raises(service.NotificationNotFoundError):
        service.mark_read(db_session, user_id=user.id, notification_id=uuid.uuid4())


def test_mark_all_read_only_affects_the_calling_user(db_session: Session) -> None:
    user_a = make_user(db_session)
    user_b = make_user(db_session)
    notification_a = make_notification(db_session, user_id=user_a.id, dedup_key="A")
    notification_b = make_notification(db_session, user_id=user_b.id, dedup_key="B")

    updated_count = service.mark_all_read(db_session, user_id=user_a.id)
    db_session.flush()
    db_session.expire_all()

    assert updated_count == 1
    assert db_session.get(Notification, notification_a.id).read_at is not None
    assert db_session.get(Notification, notification_b.id).read_at is None
