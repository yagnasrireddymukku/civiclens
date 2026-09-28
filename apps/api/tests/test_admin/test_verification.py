"""Verification queue and submission: default queue membership,
entity-type filtering, evidence requirement, entity/source validation,
and the verification -> entity.verification_status/search-index sync.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.admin import service
from app.admin.enums import AdminEntityType
from app.search.models import SearchDocument
from app.sources.enums import VerificationStatus
from tests.test_auth._helpers import make_user
from tests.test_documents._helpers import make_organization, make_scheme, make_service, make_state
from tests.test_jobs._helpers import make_job
from tests.test_tracking._helpers import make_source


def _fixtures(db_session: Session):
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    return state, source, organization


def test_verification_queue_defaults_to_needs_review_and_unverified(db_session: Session) -> None:
    state, source, organization = _fixtures(db_session)
    needs_review = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        verification_status=VerificationStatus.NEEDS_REVIEW,
    )
    unverified = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        verification_status=VerificationStatus.UNVERIFIED,
    )
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        verification_status=VerificationStatus.VERIFIED,
    )

    result = service.get_verification_queue(db_session)

    ids = {entry.entity_id for entry in result.entries}
    assert needs_review.id in ids
    assert unverified.id in ids
    assert result.total_count == 2


def test_verification_queue_filters_by_entity_type(db_session: Session) -> None:
    state, source, organization = _fixtures(db_session)
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        verification_status=VerificationStatus.UNVERIFIED,
    )
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        state=state,
        verification_status=VerificationStatus.UNVERIFIED,
    )

    result = service.get_verification_queue(db_session, entity_type=AdminEntityType.SCHEME)

    assert result.total_count == 1
    assert result.entries[0].entity_type == AdminEntityType.SCHEME


def test_submit_verification_creates_a_record_and_updates_the_entity(db_session: Session) -> None:
    state, source, organization = _fixtures(db_session)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        verification_status=VerificationStatus.NEEDS_REVIEW,
    )
    reviewer = make_user(db_session)

    record = service.submit_verification(
        db_session,
        entity_type=AdminEntityType.JOB,
        entity_id=job.id,
        status=VerificationStatus.VERIFIED,
        source_id=source.id,
        verified_by=reviewer.id,
    )

    assert record.status == VerificationStatus.VERIFIED
    assert record.verified_by == reviewer.id
    assert record.source_id == source.id
    db_session.refresh(job)
    assert job.verification_status == VerificationStatus.VERIFIED


def test_submit_verification_syncs_the_search_index(db_session: Session) -> None:
    state, source, organization = _fixtures(db_session)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        verification_status=VerificationStatus.UNVERIFIED,
    )
    reviewer = make_user(db_session)

    assert (
        db_session.query(SearchDocument)
        .filter_by(entity_type="job", entity_id=job.id)
        .one_or_none()
        is None
    )

    service.submit_verification(
        db_session,
        entity_type=AdminEntityType.JOB,
        entity_id=job.id,
        status=VerificationStatus.VERIFIED,
        source_id=source.id,
        verified_by=reviewer.id,
    )

    assert (
        db_session.query(SearchDocument)
        .filter_by(entity_type="job", entity_id=job.id)
        .one_or_none()
        is not None
    )


def test_submit_verification_rejects_a_nonexistent_entity(db_session: Session) -> None:
    _, source, _ = _fixtures(db_session)
    reviewer = make_user(db_session)

    with pytest.raises(service.EntityNotFoundError):
        service.submit_verification(
            db_session,
            entity_type=AdminEntityType.JOB,
            entity_id=uuid.uuid4(),
            status=VerificationStatus.VERIFIED,
            source_id=source.id,
            verified_by=reviewer.id,
        )


def test_submit_verification_rejects_a_nonexistent_source(db_session: Session) -> None:
    state, source, organization = _fixtures(db_session)
    job = make_job(db_session, organization=organization, state=state, source=source)
    reviewer = make_user(db_session)

    with pytest.raises(service.SourceNotFoundError):
        service.submit_verification(
            db_session,
            entity_type=AdminEntityType.JOB,
            entity_id=job.id,
            status=VerificationStatus.VERIFIED,
            source_id=uuid.uuid4(),
            verified_by=reviewer.id,
        )


def test_submit_verification_downgrading_to_needs_review_removes_from_search(
    db_session: Session,
) -> None:
    state, source, organization = _fixtures(db_session)
    service_entity = make_service(
        db_session,
        organization=organization,
        source=source,
        state=state,
        verification_status=VerificationStatus.VERIFIED,
    )
    from app.services.service import sync_service_search_index

    sync_service_search_index(db_session, service_entity)
    reviewer = make_user(db_session)

    service.submit_verification(
        db_session,
        entity_type=AdminEntityType.SERVICE,
        entity_id=service_entity.id,
        status=VerificationStatus.UNVERIFIED,
        source_id=source.id,
        verified_by=reviewer.id,
    )

    assert (
        db_session.query(SearchDocument)
        .filter_by(entity_type="service", entity_id=service_entity.id)
        .one_or_none()
        is None
    )
