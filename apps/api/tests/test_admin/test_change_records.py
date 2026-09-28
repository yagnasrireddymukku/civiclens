"""Change-record review queue: listing/filtering, approve/reject,
invalid-transition enforcement, idempotent re-decision, and the
approve -> notification-generation integration.
"""

import pytest
from sqlalchemy.orm import Session

from app.admin import service
from app.notifications.models import Notification
from app.sources.enums import ChangeReviewStatus
from app.tracking.enums import TrackedEntityType
from tests.test_auth._helpers import make_user
from tests.test_documents._helpers import make_organization, make_source, make_state
from tests.test_jobs._helpers import make_job
from tests.test_tracking._helpers import make_change_record, make_tracked_item


def _job_fixture(db_session: Session):
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    return job


def test_list_change_records_filters_by_review_status(db_session: Session) -> None:
    job = _job_fixture(db_session)
    make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
        review_status=ChangeReviewStatus.PENDING,
    )
    make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="deadline",
        old_value="2026-01-01",
        new_value="2026-02-01",
        review_status=ChangeReviewStatus.APPROVED,
    )

    pending_only = service.list_change_records(db_session, review_status=ChangeReviewStatus.PENDING)
    assert pending_only.total_count == 1
    assert pending_only.entries[0].record.field == "publication_status"

    all_records = service.list_change_records(db_session)
    assert all_records.total_count == 2


def test_list_change_records_includes_entity_display_data(db_session: Session) -> None:
    job = _job_fixture(db_session)
    make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
    )

    result = service.list_change_records(db_session)
    entry = result.entries[0]
    assert entry.display.title == job.title
    assert entry.display.route == f"/jobs/{job.slug}"
    assert entry.display.verification_status == job.verification_status


def test_list_change_records_handles_a_deleted_entity_gracefully(db_session: Session) -> None:
    job = _job_fixture(db_session)
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
    )
    db_session.delete(job)
    db_session.flush()

    result = service.list_change_records(db_session)
    assert result.entries[0].record.id == record.id
    assert result.entries[0].display.title is None
    assert result.entries[0].display.route is None


def test_approve_change_record_sets_reviewer_and_timestamp(db_session: Session) -> None:
    job = _job_fixture(db_session)
    reviewer = make_user(db_session)
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
    )

    entry = service.approve_change_record(
        db_session, change_record_id=record.id, reviewed_by=reviewer.id
    )

    assert entry.record.review_status == ChangeReviewStatus.APPROVED
    assert entry.record.reviewed_by == reviewer.id
    assert entry.record.applied_at is not None


def test_reject_change_record_sets_reviewer_without_applying(db_session: Session) -> None:
    job = _job_fixture(db_session)
    reviewer = make_user(db_session)
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
    )

    entry = service.reject_change_record(
        db_session, change_record_id=record.id, reviewed_by=reviewer.id
    )

    assert entry.record.review_status == ChangeReviewStatus.REJECTED
    assert entry.record.reviewed_by == reviewer.id
    assert entry.record.applied_at is None


def test_approving_an_already_rejected_record_is_an_invalid_transition(db_session: Session) -> None:
    job = _job_fixture(db_session)
    reviewer = make_user(db_session)
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
        review_status=ChangeReviewStatus.REJECTED,
    )

    with pytest.raises(service.InvalidChangeRecordTransitionError):
        service.approve_change_record(
            db_session, change_record_id=record.id, reviewed_by=reviewer.id
        )


def test_rejecting_an_already_approved_record_is_an_invalid_transition(db_session: Session) -> None:
    job = _job_fixture(db_session)
    reviewer = make_user(db_session)
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
        review_status=ChangeReviewStatus.APPROVED,
    )

    with pytest.raises(service.InvalidChangeRecordTransitionError):
        service.reject_change_record(
            db_session, change_record_id=record.id, reviewed_by=reviewer.id
        )


def test_reapproving_an_already_approved_record_is_idempotent(db_session: Session) -> None:
    job = _job_fixture(db_session)
    reviewer = make_user(db_session)
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
    )

    first = service.approve_change_record(
        db_session, change_record_id=record.id, reviewed_by=reviewer.id
    )
    second = service.approve_change_record(
        db_session, change_record_id=record.id, reviewed_by=reviewer.id
    )

    assert first.record.applied_at == second.record.applied_at
    assert second.record.review_status == ChangeReviewStatus.APPROVED


def test_approve_raises_not_found_for_a_nonexistent_record(db_session: Session) -> None:
    reviewer = make_user(db_session)
    import uuid

    with pytest.raises(service.ChangeRecordNotFoundError):
        service.approve_change_record(
            db_session, change_record_id=uuid.uuid4(), reviewed_by=reviewer.id
        )


def test_approving_a_change_record_generates_a_notification_for_trackers(
    db_session: Session,
) -> None:
    job = _job_fixture(db_session)
    tracker = make_user(db_session)
    reviewer = make_user(db_session)
    make_tracked_item(
        db_session, user_id=tracker.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
    )

    service.approve_change_record(db_session, change_record_id=record.id, reviewed_by=reviewer.id)

    notifications = db_session.query(Notification).filter_by(user_id=tracker.id).all()
    assert len(notifications) == 1
    assert notifications[0].change_record_id == record.id


def test_rejecting_a_change_record_never_generates_a_notification(db_session: Session) -> None:
    job = _job_fixture(db_session)
    tracker = make_user(db_session)
    reviewer = make_user(db_session)
    make_tracked_item(
        db_session, user_id=tracker.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
    )

    service.reject_change_record(db_session, change_record_id=record.id, reviewed_by=reviewer.id)

    assert db_session.query(Notification).filter_by(user_id=tracker.id).count() == 0


def test_approving_twice_never_duplicates_the_notification(db_session: Session) -> None:
    job = _job_fixture(db_session)
    tracker = make_user(db_session)
    reviewer = make_user(db_session)
    make_tracked_item(
        db_session, user_id=tracker.id, entity_type=TrackedEntityType.JOB, entity_id=job.id
    )
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
    )

    service.approve_change_record(db_session, change_record_id=record.id, reviewed_by=reviewer.id)
    service.approve_change_record(db_session, change_record_id=record.id, reviewed_by=reviewer.id)

    assert db_session.query(Notification).filter_by(user_id=tracker.id).count() == 1
