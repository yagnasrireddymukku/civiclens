"""Database-level constraint tests for `Notification` — the `UNIQUE
(user_id, dedup_key)` constraint that enforces deduplication at the
database layer (this phase's explicit "enforce notification
deduplication at the database level when feasible"), and cascade
delete to `NotificationDeliveryAttempt`.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.notifications.enums import DeliveryChannel, DeliveryStatus, NotificationType
from app.notifications.models import Notification, NotificationDeliveryAttempt
from tests.test_auth._helpers import make_user
from tests.test_notifications._helpers import make_notification


def test_duplicate_dedup_key_for_the_same_user_is_rejected(db_session: Session) -> None:
    user = make_user(db_session)
    make_notification(db_session, user_id=user.id, dedup_key="SAME_KEY")

    db_session.add(
        Notification(
            user_id=user.id,
            notification_type=NotificationType.CHANGE_DETECTED,
            title="Second",
            body="Second body.",
            dedup_key="SAME_KEY",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_dedup_key_is_allowed_for_two_different_users(db_session: Session) -> None:
    user_a = make_user(db_session)
    user_b = make_user(db_session)
    make_notification(db_session, user_id=user_a.id, dedup_key="SHARED_KEY")
    make_notification(db_session, user_id=user_b.id, dedup_key="SHARED_KEY")  # must not raise


def test_deleting_notification_cascades_to_delivery_attempts(db_session: Session) -> None:
    user = make_user(db_session)
    notification = make_notification(db_session, user_id=user.id)
    attempt = NotificationDeliveryAttempt(
        notification_id=notification.id,
        channel=DeliveryChannel.IN_APP,
        status=DeliveryStatus.SENT,
        attempt_number=1,
    )
    db_session.add(attempt)
    db_session.flush()
    attempt_id = attempt.id

    db_session.delete(notification)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(NotificationDeliveryAttempt, attempt_id) is None


def test_deleting_user_cascades_to_their_notifications(db_session: Session) -> None:
    user = make_user(db_session)
    notification = make_notification(db_session, user_id=user.id)
    notification_id = notification.id

    db_session.delete(user)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(Notification, notification_id) is None
