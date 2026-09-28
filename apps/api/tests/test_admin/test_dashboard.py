"""Admin dashboard metrics — real, data-backed counts and activity
only (this phase's explicit "do not introduce fabricated dashboard
statistics").
"""

from sqlalchemy.orm import Session

from app.admin import service
from app.sources.enums import ChangeReviewStatus, VerificationStatus
from app.tracking.enums import TrackedEntityType
from tests.test_auth._helpers import make_user
from tests.test_documents._helpers import make_organization, make_state
from tests.test_jobs._helpers import make_job
from tests.test_tracking._helpers import make_change_record, make_source


def test_dashboard_reports_pending_change_record_count(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
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

    metrics = service.get_dashboard_metrics(db_session)

    assert metrics.pending_change_records == 1


def test_dashboard_reports_verification_status_distribution(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        verification_status=VerificationStatus.VERIFIED,
    )
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        verification_status=VerificationStatus.NEEDS_REVIEW,
    )

    metrics = service.get_dashboard_metrics(db_session)

    assert metrics.verification_status_counts[VerificationStatus.VERIFIED] >= 1
    assert metrics.verification_status_counts[VerificationStatus.NEEDS_REVIEW] >= 1


def test_dashboard_lists_recent_change_decisions_excluding_pending(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    reviewer = make_user(db_session)
    pending = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
        review_status=ChangeReviewStatus.PENDING,
    )
    decided = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="deadline",
        old_value="2026-01-01",
        new_value="2026-02-01",
        review_status=ChangeReviewStatus.APPROVED,
        reviewed_by=reviewer.id,
    )

    metrics = service.get_dashboard_metrics(db_session)

    ids = {r.id for r in metrics.recent_change_decisions}
    assert decided.id in ids
    assert pending.id not in ids
