"""Notification-generation tests — this phase's core "never notify from
unverified information" property: deadline reminders only for a real
deadline within the configured window; change notifications only for
an **approved** `ChangeRecord` (never `PENDING`/`REJECTED`); entity-
unavailability notifications only once `search_documents` no longer
has the entity.
"""

import datetime

from sqlalchemy.orm import Session

from app.jobs.enums import JobNotificationStatus, JobPublicationStatus
from app.jobs.service import sync_job_search_index
from app.notifications import generation
from app.notifications.enums import NotificationType
from app.notifications.models import Notification
from app.sources.enums import ChangeReviewStatus
from app.tracking.enums import TrackedEntityType
from tests.test_auth._helpers import make_user
from tests.test_documents._helpers import make_organization, make_source, make_state
from tests.test_jobs._helpers import make_job
from tests.test_jobs._helpers import make_notification as make_job_notification
from tests.test_tracking._helpers import make_change_record, make_tracked_item


def test_deadline_reminder_fires_within_the_configured_window(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    make_job_notification(
        db_session,
        job,
        source=source,
        status=JobNotificationStatus.PUBLISHED,
        application_end=datetime.date(2026, 8, 5),
    )
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    now = datetime.datetime(2026, 8, 3, 12, 0, tzinfo=datetime.UTC)
    created = generation.generate_deadline_reminders(db_session, reminder_days_before=3, now=now)

    assert created == 1
    notification = db_session.query(Notification).filter_by(user_id=user.id).one()
    assert notification.notification_type == NotificationType.DEADLINE_REMINDER


def test_deadline_reminder_does_not_fire_outside_the_window(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    make_job_notification(
        db_session,
        job,
        source=source,
        status=JobNotificationStatus.PUBLISHED,
        application_end=datetime.date(2026, 12, 31),
    )
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    now = datetime.datetime(2026, 8, 3, 12, 0, tzinfo=datetime.UTC)  # far from Dec 31
    created = generation.generate_deadline_reminders(db_session, reminder_days_before=3, now=now)

    assert created == 0


def test_deadline_reminder_does_not_fire_for_an_already_expired_deadline(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    make_job_notification(
        db_session,
        job,
        source=source,
        status=JobNotificationStatus.PUBLISHED,
        application_end=datetime.date(2026, 1, 1),
    )
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    now = datetime.datetime(2026, 8, 3, 12, 0, tzinfo=datetime.UTC)
    created = generation.generate_deadline_reminders(db_session, reminder_days_before=3, now=now)

    assert created == 0


def test_deadline_reminder_is_deduplicated_across_repeated_runs(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    make_job_notification(
        db_session,
        job,
        source=source,
        status=JobNotificationStatus.PUBLISHED,
        application_end=datetime.date(2026, 8, 5),
    )
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    now = datetime.datetime(2026, 8, 3, 12, 0, tzinfo=datetime.UTC)

    first_run = generation.generate_deadline_reminders(db_session, reminder_days_before=3, now=now)
    second_run = generation.generate_deadline_reminders(db_session, reminder_days_before=3, now=now)

    assert first_run == 1
    assert second_run == 0


def test_change_notification_fires_only_for_an_approved_change_record(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    pending = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
        review_status=ChangeReviewStatus.PENDING,
    )
    created_while_pending = generation.generate_change_notifications(db_session)
    assert created_while_pending == 0

    pending.review_status = ChangeReviewStatus.APPROVED
    db_session.flush()
    created_after_approval = generation.generate_change_notifications(db_session)
    assert created_after_approval == 1


def test_rejected_change_record_never_notifies(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
        review_status=ChangeReviewStatus.REJECTED,
    )

    assert generation.generate_change_notifications(db_session) == 0


def test_change_notification_only_reaches_users_tracking_that_entity(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    tracker = make_user(db_session)
    non_tracker = make_user(db_session)
    make_tracked_item(
        db_session, user_id=tracker.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
        review_status=ChangeReviewStatus.APPROVED,
    )

    generation.generate_change_notifications(db_session)

    assert db_session.query(Notification).filter_by(user_id=tracker.id).count() == 1
    assert db_session.query(Notification).filter_by(user_id=non_tracker.id).count() == 0


def test_unavailability_notification_fires_once_entity_leaves_search(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        publication_status=JobPublicationStatus.PUBLISHED,
    )
    sync_job_search_index(db_session, job)
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    assert generation.generate_unavailability_notifications(db_session) == 0

    job.publication_status = JobPublicationStatus.DRAFT
    db_session.flush()
    sync_job_search_index(db_session, job)  # removes it from search_documents

    created = generation.generate_unavailability_notifications(db_session)
    assert created == 1
    notification = db_session.query(Notification).filter_by(user_id=user.id).one()
    assert notification.notification_type == NotificationType.ENTITY_NO_LONGER_AVAILABLE


def test_unavailability_notification_is_deduplicated(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        publication_status=JobPublicationStatus.DRAFT,
    )
    user = make_user(db_session)
    make_tracked_item(
        db_session, user_id=user.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )

    first_run = generation.generate_unavailability_notifications(db_session)
    second_run = generation.generate_unavailability_notifications(db_session)

    assert first_run == 1
    assert second_run == 0
