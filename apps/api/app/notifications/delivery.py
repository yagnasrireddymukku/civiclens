"""Email delivery — bounded, persisted-before-attempted, idempotent
(this phase's §8/§4.7: "do not rely on untracked fire-and-forget tasks
for durable delivery. Persist pending work before delivery... bounded
and observable retries").

In-app delivery needs none of this: writing a `Notification` row *is*
delivery for that channel (`app.notifications.service.create_notification`
records the `IN_APP` attempt as `SENT` immediately, at creation time).
This module only ever concerns the optional, provider-backed `EMAIL`
channel, and is a no-op (not an error) when no provider is configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.notifications.email_provider import EmailProvider, EmailProviderError
from app.notifications.enums import DeliveryChannel, DeliveryStatus
from app.notifications.models import Notification, NotificationDeliveryAttempt
from app.users.models import User


@dataclass(frozen=True, slots=True)
class DeliverySummary:
    attempted: int
    sent: int
    failed: int
    provider_configured: bool


async def deliver_pending_emails(
    session: Session, *, email_provider: EmailProvider | None, max_attempts: int
) -> DeliverySummary:
    if email_provider is None:
        return DeliverySummary(attempted=0, sent=0, failed=0, provider_configured=False)

    candidates = (
        session.query(Notification)
        .join(User, Notification.user_id == User.id)
        .filter(User.email_notifications_enabled.is_(True))
        .all()
    )

    attempted = sent = failed = 0
    for notification in candidates:
        email_attempts = [
            a for a in notification.delivery_attempts if a.channel == DeliveryChannel.EMAIL
        ]
        if any(a.status == DeliveryStatus.SENT for a in email_attempts):
            continue  # already delivered — never re-send
        if len(email_attempts) >= max_attempts:
            continue  # retries exhausted — stays FAILED, bounded, not retried forever

        user = session.get(User, notification.user_id)
        if user is None:  # pragma: no cover - FK guarantees this in practice
            continue

        # Persisted *before* the provider call, per this phase's
        # explicit requirement — a crash between here and the provider
        # responding leaves a durable, retryable `PENDING` row rather
        # than silently losing the delivery intent.
        attempt = NotificationDeliveryAttempt(
            notification_id=notification.id,
            channel=DeliveryChannel.EMAIL,
            status=DeliveryStatus.PENDING,
            attempt_number=len(email_attempts) + 1,
            attempted_at=datetime.now(UTC),
        )
        session.add(attempt)
        session.flush()
        attempted += 1

        try:
            await email_provider.send(
                to=user.email, subject=notification.title, body=notification.body
            )
        except EmailProviderError as exc:
            attempt.status = DeliveryStatus.FAILED
            attempt.error = str(exc)
            failed += 1
        else:
            attempt.status = DeliveryStatus.SENT
            sent += 1

    return DeliverySummary(attempted=attempted, sent=sent, failed=failed, provider_configured=True)
