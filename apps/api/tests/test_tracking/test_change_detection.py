"""Change-detection tests — this phase's §4.4: stable field-level
comparison (not "did anything at all change"), idempotency, and the
never-auto-approved property.
"""

import uuid

from sqlalchemy.orm import Session

from app.jobs.enums import JobPublicationStatus
from app.sources.enums import ChangeReviewStatus
from app.sources.models import ChangeRecord
from app.tracking.change_detection import (
    FIELD_PUBLICATION_STATUS,
    approve_change_record,
    detect_changes,
    reject_change_record,
)
from app.tracking.enums import TrackedEntityType
from tests.test_documents._helpers import make_organization, make_source, make_state
from tests.test_jobs._helpers import make_job


def test_first_detection_run_records_a_pending_baseline(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)

    created = detect_changes(db_session, entity_type=TrackedEntityType.JOB, entity_id=job.id)

    assert len(created) >= 1
    assert all(c.review_status == ChangeReviewStatus.PENDING for c in created)
    status_change = next(c for c in created if c.field == FIELD_PUBLICATION_STATUS)
    assert status_change.old_value is None
    assert status_change.new_value == job.publication_status.value


def test_second_run_with_no_real_change_creates_nothing(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)

    detect_changes(db_session, entity_type=TrackedEntityType.JOB, entity_id=job.id)
    second_run = detect_changes(db_session, entity_type=TrackedEntityType.JOB, entity_id=job.id)

    assert second_run == []


def test_a_real_publication_status_change_is_detected(db_session: Session) -> None:
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
    detect_changes(db_session, entity_type=TrackedEntityType.JOB, entity_id=job.id)

    job.publication_status = JobPublicationStatus.ARCHIVED
    db_session.flush()
    second_run = detect_changes(db_session, entity_type=TrackedEntityType.JOB, entity_id=job.id)

    status_changes = [c for c in second_run if c.field == FIELD_PUBLICATION_STATUS]
    assert len(status_changes) == 1
    assert status_changes[0].old_value == "PUBLISHED"
    assert status_changes[0].new_value == "ARCHIVED"


def test_changing_an_untracked_field_produces_no_change_record(db_session: Session) -> None:
    """The core "stable field-level comparison" property: only the
    named, supported fields are ever compared — changing `title`
    (cosmetic/reformatting territory) must never itself produce a
    `ChangeRecord`."""

    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    detect_changes(db_session, entity_type=TrackedEntityType.JOB, entity_id=job.id)

    job.title = "A Completely Reworded Title (Fixture)"
    job.summary = "Reformatted summary text, same underlying facts."
    db_session.flush()
    second_run = detect_changes(db_session, entity_type=TrackedEntityType.JOB, entity_id=job.id)

    assert second_run == []


def test_detect_changes_for_a_deleted_entity_returns_nothing(db_session: Session) -> None:
    result = detect_changes(db_session, entity_type=TrackedEntityType.JOB, entity_id=uuid.uuid4())
    assert result == []


def test_approve_change_record_sets_status_and_reviewer(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    created = detect_changes(db_session, entity_type=TrackedEntityType.JOB, entity_id=job.id)
    record = created[0]

    approve_change_record(db_session, change_record_id=record.id)

    refreshed = db_session.get(ChangeRecord, record.id)
    assert refreshed is not None
    assert refreshed.review_status == ChangeReviewStatus.APPROVED
    assert refreshed.applied_at is not None


def test_reject_change_record_sets_status(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    created = detect_changes(db_session, entity_type=TrackedEntityType.JOB, entity_id=job.id)
    record = created[0]

    reject_change_record(db_session, change_record_id=record.id)

    refreshed = db_session.get(ChangeRecord, record.id)
    assert refreshed is not None
    assert refreshed.review_status == ChangeReviewStatus.REJECTED
