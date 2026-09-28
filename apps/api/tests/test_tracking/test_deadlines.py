"""Deadline semantics tests — this phase's §4.3: explicit timezone
handling, inclusive end-of-day boundaries, and "no structured deadline
exists" honestly returning `None` rather than a guess.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.jobs.enums import JobNotificationStatus
from app.tracking.deadlines import (
    IST,
    deadline_end_instant,
    get_deadline_for_entity,
    is_expired,
    time_to_deadline,
)
from app.tracking.enums import TrackedEntityType
from tests.test_documents._helpers import make_organization, make_service, make_source, make_state
from tests.test_jobs._helpers import make_job, make_notification


def test_deadline_end_instant_is_end_of_day_ist() -> None:
    instant = deadline_end_instant(date(2026, 12, 31))
    assert instant.tzinfo is not None
    assert instant.astimezone(IST).hour == 23
    assert instant.astimezone(IST).minute == 59
    assert instant.astimezone(IST).second == 59


def test_is_expired_false_exactly_at_the_boundary() -> None:
    deadline = date(2026, 12, 31)
    now = deadline_end_instant(deadline)
    assert is_expired(deadline, now=now) is False


def test_is_expired_true_one_second_after_the_boundary() -> None:
    deadline = date(2026, 12, 31)
    now = deadline_end_instant(deadline) + timedelta(seconds=1)
    assert is_expired(deadline, now=now) is True


def test_is_expired_false_earlier_the_same_day() -> None:
    deadline = date(2026, 12, 31)
    now = datetime(2026, 12, 31, 0, 0, 1, tzinfo=IST)
    assert is_expired(deadline, now=now) is False


def test_deadline_boundary_is_computed_correctly_regardless_of_caller_timezone() -> None:
    """A deadline of Dec 31 IST end-of-day is 18:29:59 UTC — a caller
    passing `now` in UTC must get the same boundary as one passing IST,
    since both are the same instant."""

    deadline = date(2026, 12, 31)
    just_before_utc = datetime(2026, 12, 31, 18, 29, 59, tzinfo=UTC)
    just_after_utc = datetime(2026, 12, 31, 18, 30, 1, tzinfo=UTC)
    assert is_expired(deadline, now=just_before_utc) is False
    assert is_expired(deadline, now=just_after_utc) is True


def test_time_to_deadline_is_positive_before_and_negative_after() -> None:
    deadline = date(2026, 12, 31)
    before = deadline_end_instant(deadline) - timedelta(days=1)
    after = deadline_end_instant(deadline) + timedelta(days=1)
    assert time_to_deadline(deadline, now=before) > timedelta(0)
    assert time_to_deadline(deadline, now=after) < timedelta(0)


def test_get_deadline_for_job_reads_the_notifications_application_end(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    make_notification(
        db_session,
        job,
        source=source,
        status=JobNotificationStatus.PUBLISHED,
        application_end=date(2026, 12, 31),
    )

    deadline = get_deadline_for_entity(db_session, TrackedEntityType.JOB, job.id)
    assert deadline == date(2026, 12, 31)


def test_get_deadline_for_job_returns_none_without_a_stated_deadline(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    make_notification(
        db_session, job, source=source, status=JobNotificationStatus.PUBLISHED, application_end=None
    )

    assert get_deadline_for_entity(db_session, TrackedEntityType.JOB, job.id) is None


def test_get_deadline_for_job_picks_the_most_recently_created_notification(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    make_notification(
        db_session,
        job,
        source=source,
        status=JobNotificationStatus.PUBLISHED,
        application_end=date(2025, 1, 1),
    )
    make_notification(
        db_session,
        job,
        source=source,
        status=JobNotificationStatus.PUBLISHED,
        application_end=date(2026, 12, 31),
    )

    assert get_deadline_for_entity(db_session, TrackedEntityType.JOB, job.id) == date(2026, 12, 31)


def test_get_deadline_for_service_is_always_none(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(db_session, organization=organization, source=source)

    assert get_deadline_for_entity(db_session, TrackedEntityType.SERVICE, service.id) is None


def test_get_deadline_for_unknown_job_id_is_none(db_session: Session) -> None:
    assert get_deadline_for_entity(db_session, TrackedEntityType.JOB, uuid.uuid4()) is None
