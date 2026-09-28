"""Sweep-orchestrator tests: `run_notification_sweep` sequences change
detection then all three generators then commits once; email delivery
is a deliberately separate async step (`deliver_notification_emails`).
Uses `asyncio.run`, matching `tests/test_ai/test_providers.py`'s
convention (no pytest-asyncio/anyio plugin is installed).
"""

import asyncio
import datetime

from sqlalchemy.orm import Session

from app.notifications import jobs
from app.notifications.email_provider import EmailProviderError
from app.notifications.enums import NotificationType
from app.notifications.models import Notification
from app.sources.models import ChangeRecord
from app.tracking.enums import TrackedEntityType
from tests.test_auth._helpers import make_user
from tests.test_documents._helpers import make_organization, make_source, make_state
from tests.test_jobs._helpers import make_job
from tests.test_jobs._helpers import make_notification as make_job_notification
from tests.test_tracking._helpers import make_tracked_item


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


def test_sweep_detects_changes_for_currently_tracked_entities_only(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    tracked_job = make_job(db_session, organization=organization, state=state, source=source)
    untracked_job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=tracked_job.id
    )

    summary = jobs.run_notification_sweep(
        db_session, reminder_days_before=3, email_provider=None, email_max_attempts=3
    )

    assert summary.change_records_detected == 1  # first-ever observation of publication_status
    tracked_records = db_session.query(ChangeRecord).filter_by(entity_id=tracked_job.id).count()
    untracked_records = db_session.query(ChangeRecord).filter_by(entity_id=untracked_job.id).count()
    assert tracked_records == 1
    assert untracked_records == 0


def test_sweep_generates_a_deadline_reminder_for_a_tracked_item_with_a_near_deadline(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    today = datetime.datetime.now(datetime.UTC).date()
    make_job_notification(
        db_session,
        job,
        source=source,
        application_end=today + datetime.timedelta(days=1),
    )
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    summary = jobs.run_notification_sweep(
        db_session, reminder_days_before=3, email_provider=None, email_max_attempts=3
    )

    assert summary.deadline_reminders_created == 1
    notification = (
        db_session.query(Notification)
        .filter_by(user_id=user.id, notification_type=NotificationType.DEADLINE_REMINDER)
        .one()
    )
    assert notification.entity_id == job.id


def test_sweep_is_idempotent_across_repeated_runs(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    first = jobs.run_notification_sweep(
        db_session, reminder_days_before=3, email_provider=None, email_max_attempts=3
    )
    second = jobs.run_notification_sweep(
        db_session, reminder_days_before=3, email_provider=None, email_max_attempts=3
    )

    assert first.change_records_detected == 1  # first-ever observation
    assert second.change_records_detected == 0  # no actual field change since
    assert second.change_notifications_created == 0


def test_sweep_does_not_deliver_email_itself(db_session: Session) -> None:
    """`run_notification_sweep` never calls the email provider — delivery
    is `deliver_notification_emails`'s job (kept separate: sync ORM work
    vs. an async provider call, per `app/notifications/jobs.py`'s
    docstring)."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session, email_notifications_enabled=True)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    summary = jobs.run_notification_sweep(
        db_session,
        reminder_days_before=3,
        email_provider=_RecordingProvider(),
        email_max_attempts=3,
    )

    assert summary.email_delivery.attempted == 0
    assert summary.email_delivery.provider_configured is False


def test_deliver_notification_emails_sends_and_commits(db_session: Session) -> None:
    user = make_user(db_session, email_notifications_enabled=True)
    from tests.test_notifications._helpers import make_notification as make_inbox_notification

    make_inbox_notification(db_session, user_id=user.id)
    provider = _RecordingProvider()

    summary = _sync(
        jobs.deliver_notification_emails(db_session, email_provider=provider, max_attempts=3)
    )

    assert summary.sent == 1
    assert len(provider.sent) == 1


def test_deliver_notification_emails_records_failures_without_raising(db_session: Session) -> None:
    user = make_user(db_session, email_notifications_enabled=True)
    from tests.test_notifications._helpers import make_notification as make_inbox_notification

    make_inbox_notification(db_session, user_id=user.id)
    provider = _AlwaysFailingProvider()

    summary = _sync(
        jobs.deliver_notification_emails(db_session, email_provider=provider, max_attempts=3)
    )

    assert summary.failed == 1
