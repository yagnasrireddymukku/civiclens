"""The one entry point that runs a full tracking → notification sweep:
change detection → notification generation → email delivery. Callable
by a manual ops script (`scripts/run_notification_sweep.py`) or a
future external scheduler (cron, systemd timer, a managed platform's
scheduled-job feature) — **nothing in this codebase invokes this on a
recurring basis today** (this phase's explicit "do not pretend a
recurring process is running when it is not").

Change detection runs for every entity any user currently tracks (not
every entity in the system) — this phase scopes work to what's actually
being watched, not a full-catalog scan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.notifications import generation
from app.notifications.delivery import DeliverySummary, deliver_pending_emails
from app.notifications.email_provider import EmailProvider
from app.tracking.change_detection import detect_changes
from app.tracking.models import TrackedItem
from app.tracking.service import entity_type_and_id


@dataclass(frozen=True, slots=True)
class SweepSummary:
    change_records_detected: int
    deadline_reminders_created: int
    change_notifications_created: int
    unavailability_notifications_created: int
    email_delivery: DeliverySummary


def run_notification_sweep(
    session: Session,
    *,
    reminder_days_before: int,
    email_provider: EmailProvider | None,
    email_max_attempts: int,
) -> SweepSummary:
    """Synchronous change-detection/generation, async email delivery —
    callers in an async context (the ops script, a future scheduler)
    call this directly; a sync caller uses `asyncio.run` around just the
    delivery half if needed. Commits once, at the end, so a failure
    partway through change detection never leaves a half-written sweep
    committed."""

    now = datetime.now(UTC)

    detected = 0
    tracked_entities = {
        entity_type_and_id(item)
        for item in session.query(TrackedItem).filter(TrackedItem.is_active.is_(True)).all()
    }
    for entity_type, entity_id in tracked_entities:
        detected += len(detect_changes(session, entity_type=entity_type, entity_id=entity_id))

    deadline_reminders = generation.generate_deadline_reminders(
        session, reminder_days_before=reminder_days_before, now=now
    )
    change_notifications = generation.generate_change_notifications(session)
    unavailability_notifications = generation.generate_unavailability_notifications(session)

    session.commit()

    return SweepSummary(
        change_records_detected=detected,
        deadline_reminders_created=deadline_reminders,
        change_notifications_created=change_notifications,
        unavailability_notifications_created=unavailability_notifications,
        email_delivery=DeliverySummary(attempted=0, sent=0, failed=0, provider_configured=False),
    )


async def deliver_notification_emails(
    session: Session, *, email_provider: EmailProvider | None, max_attempts: int
) -> DeliverySummary:
    """Separate async step — see `run_notification_sweep`'s docstring
    for why detection/generation and delivery are split rather than one
    function mixing sync ORM work with an async provider call."""

    summary = await deliver_pending_emails(
        session, email_provider=email_provider, max_attempts=max_attempts
    )
    session.commit()
    return summary
