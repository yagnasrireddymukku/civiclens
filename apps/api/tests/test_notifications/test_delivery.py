"""Email delivery tests — bounded retries, "already sent" and
"provider disabled" no-ops, persisted-before-attempted ordering, and
error recording. Uses in-process fake `EmailProvider` implementations
(never a real network call — docs/TESTING.md's "never claim real email
delivery tested if only mocked"). Async calls are run via
`asyncio.run`, matching `tests/test_ai/test_providers.py`'s convention
(no pytest-asyncio/anyio plugin is installed).
"""

import asyncio

from sqlalchemy.orm import Session

from app.notifications import delivery
from app.notifications.email_provider import EmailProviderError
from app.notifications.enums import DeliveryChannel, DeliveryStatus
from tests.test_auth._helpers import make_user
from tests.test_notifications._helpers import make_notification


def _sync(coro):
    return asyncio.run(coro)


class _RecordingProvider:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))


class _AlwaysFailingProvider:
    async def send(self, *, to: str, subject: str, body: str) -> None:
        raise EmailProviderError("simulated provider failure")


def test_delivery_is_a_no_op_when_no_provider_is_configured(db_session: Session) -> None:
    user = make_user(db_session, email_notifications_enabled=True)
    make_notification(db_session, user_id=user.id)

    summary = _sync(
        delivery.deliver_pending_emails(db_session, email_provider=None, max_attempts=3)
    )

    assert summary.provider_configured is False
    assert summary.attempted == 0


def test_delivery_skips_users_with_email_notifications_disabled(db_session: Session) -> None:
    user = make_user(db_session, email_notifications_enabled=False)
    make_notification(db_session, user_id=user.id)
    provider = _RecordingProvider()

    summary = _sync(
        delivery.deliver_pending_emails(db_session, email_provider=provider, max_attempts=3)
    )

    assert summary.attempted == 0
    assert provider.sent == []


def test_delivery_persists_a_pending_attempt_before_calling_the_provider(
    db_session: Session,
) -> None:
    user = make_user(db_session, email_notifications_enabled=True)
    notification = make_notification(db_session, user_id=user.id)

    class _ObservingProvider:
        def __init__(self) -> None:
            self.attempt_status_when_called: DeliveryStatus | None = None

        async def send(self, *, to: str, subject: str, body: str) -> None:
            db_session.flush()
            db_session.refresh(notification)
            email_attempts = [
                a for a in notification.delivery_attempts if a.channel == DeliveryChannel.EMAIL
            ]
            self.attempt_status_when_called = email_attempts[0].status

    provider = _ObservingProvider()
    _sync(delivery.deliver_pending_emails(db_session, email_provider=provider, max_attempts=3))

    assert provider.attempt_status_when_called == DeliveryStatus.PENDING


def test_successful_delivery_marks_the_attempt_sent(db_session: Session) -> None:
    user = make_user(db_session, email_notifications_enabled=True)
    notification = make_notification(db_session, user_id=user.id)
    provider = _RecordingProvider()

    summary = _sync(
        delivery.deliver_pending_emails(db_session, email_provider=provider, max_attempts=3)
    )

    assert summary.sent == 1
    assert summary.failed == 0
    assert provider.sent == [(user.email, notification.title, notification.body)]
    db_session.flush()
    db_session.expire_all()
    email_attempts = [
        a for a in notification.delivery_attempts if a.channel == DeliveryChannel.EMAIL
    ]
    assert len(email_attempts) == 1
    assert email_attempts[0].status == DeliveryStatus.SENT


def test_a_provider_failure_is_recorded_and_does_not_raise(db_session: Session) -> None:
    user = make_user(db_session, email_notifications_enabled=True)
    notification = make_notification(db_session, user_id=user.id)
    provider = _AlwaysFailingProvider()

    summary = _sync(
        delivery.deliver_pending_emails(db_session, email_provider=provider, max_attempts=3)
    )

    assert summary.failed == 1
    db_session.flush()
    db_session.expire_all()
    email_attempts = [
        a for a in notification.delivery_attempts if a.channel == DeliveryChannel.EMAIL
    ]
    assert email_attempts[0].status == DeliveryStatus.FAILED
    assert email_attempts[0].error is not None


def test_delivery_never_reattempts_an_already_sent_notification(db_session: Session) -> None:
    user = make_user(db_session, email_notifications_enabled=True)
    make_notification(db_session, user_id=user.id)
    provider = _RecordingProvider()

    _sync(delivery.deliver_pending_emails(db_session, email_provider=provider, max_attempts=3))
    second_summary = _sync(
        delivery.deliver_pending_emails(db_session, email_provider=provider, max_attempts=3)
    )

    assert second_summary.attempted == 0
    assert len(provider.sent) == 1


def test_delivery_stops_retrying_once_max_attempts_is_reached(db_session: Session) -> None:
    user = make_user(db_session, email_notifications_enabled=True)
    notification = make_notification(db_session, user_id=user.id)
    provider = _AlwaysFailingProvider()

    for _ in range(2):
        _sync(delivery.deliver_pending_emails(db_session, email_provider=provider, max_attempts=2))
        # Simulate each sweep run starting with a fresh session: flush the
        # in-memory FAILED status set by the exception handler before
        # discarding the cached (stale) relationship collection.
        db_session.flush()
        db_session.expire_all()

    third_summary = _sync(
        delivery.deliver_pending_emails(db_session, email_provider=provider, max_attempts=2)
    )

    assert third_summary.attempted == 0
    db_session.flush()
    db_session.expire_all()
    email_attempts = [
        a for a in notification.delivery_attempts if a.channel == DeliveryChannel.EMAIL
    ]
    assert len(email_attempts) == 2
    assert all(a.status == DeliveryStatus.FAILED for a in email_attempts)
