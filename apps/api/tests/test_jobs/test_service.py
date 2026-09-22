"""Jobs domain service-layer tests: list/detail visibility, filtering,
pagination, and Civic Search index synchronization (this phase's §16).
Fixture data is unambiguously fictional (docs/DATA_GOVERNANCE.md §7).
"""

import datetime

from sqlalchemy.orm import Session

from app.jobs.enums import EmploymentType, JobPublicationStatus
from app.jobs.service import (
    SEARCH_ENTITY_TYPE,
    get_job_by_slug,
    is_publicly_visible,
    list_jobs,
    list_notifications_for_job,
    sync_job_search_index,
)
from app.search.service import search_documents
from app.sources.enums import VerificationStatus
from tests.test_jobs._helpers import (
    make_district,
    make_job,
    make_notification,
    make_organization,
    make_source,
    make_state,
    make_vacancy,
)


def test_published_verified_job_is_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)

    assert is_publicly_visible(job) is True


def test_draft_job_is_not_publicly_visible(db_session: Session) -> None:
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

    assert is_publicly_visible(job) is False


def test_unverified_job_is_not_publicly_visible_even_if_published(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        verification_status=VerificationStatus.UNVERIFIED,
    )

    assert is_publicly_visible(job) is False


def test_soft_deleted_job_is_not_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        deleted_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )

    assert is_publicly_visible(job) is False


def test_get_job_by_slug_returns_none_for_unpublished_job(db_session: Session) -> None:
    """A draft job returns None from the public read path — the route
    layer maps this to an identical 404, never distinguishing "doesn't
    exist" from "not yet published" (app/jobs/service.py's docstring)."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="draft-job",
        publication_status=JobPublicationStatus.DRAFT,
    )

    assert get_job_by_slug(db_session, "draft-job") is None


def test_get_job_by_slug_returns_row_with_joined_names(db_session: Session) -> None:
    state = make_state(db_session)
    district = make_district(db_session, state)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        district=district,
        slug="findable-job",
    )

    row = get_job_by_slug(db_session, "findable-job")

    assert row is not None
    assert row.job.slug == "findable-job"
    assert row.state_name == state.name
    assert row.district_name == district.name
    assert row.organization.id == organization.id


def test_list_jobs_excludes_unpublished_and_unverified(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(db_session, organization=organization, state=state, source=source, slug="visible-job")
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="draft-job",
        publication_status=JobPublicationStatus.DRAFT,
    )
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="unverified-job",
        verification_status=VerificationStatus.UNVERIFIED,
    )

    result = list_jobs(db_session)

    assert result.total_count == 1
    assert result.rows[0].job.slug == "visible-job"


def test_list_jobs_filters_are_applied_as_and_conditions(db_session: Session) -> None:
    state = make_state(db_session)
    other_state = make_state(db_session, name="Otherland", code="OT", slug="otherland")
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="in-state-job",
        employment_type=EmploymentType.PERMANENT,
    )
    make_job(
        db_session,
        organization=organization,
        state=other_state,
        source=source,
        slug="other-state-job",
        employment_type=EmploymentType.PERMANENT,
    )
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="contract-job",
        employment_type=EmploymentType.CONTRACT,
    )

    result = list_jobs(db_session, state_id=state.id, employment_type=EmploymentType.PERMANENT)

    assert result.total_count == 1
    assert result.rows[0].job.slug == "in-state-job"


def test_list_jobs_pagination_is_bounded_and_reports_total_count(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    for index in range(5):
        make_job(
            db_session, organization=organization, state=state, source=source, slug=f"job-{index}"
        )

    result = list_jobs(db_session, page=1, page_size=2)

    assert result.total_count == 5
    assert len(result.rows) == 2


def test_list_jobs_orders_by_recency_by_default(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="older-job",
        last_verified_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="newer-job",
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )

    result = list_jobs(db_session)

    assert result.rows[0].job.slug == "newer-job"


def test_list_notifications_for_job_returns_vacancies_grouped_correctly(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    notification_one = make_notification(db_session, job, source, notification_number="NOTIF-1")
    notification_two = make_notification(db_session, job, source, notification_number="NOTIF-2")
    make_vacancy(db_session, notification_one, post_name="Post A")
    make_vacancy(db_session, notification_one, post_name="Post B")
    make_vacancy(db_session, notification_two, post_name="Post C")

    rows = list_notifications_for_job(db_session, job.id)

    assert len(rows) == 2
    by_number = {row.notification.notification_number: row for row in rows}
    assert {v.post_name for v in by_number["NOTIF-1"].vacancies} == {"Post A", "Post B"}
    assert {v.post_name for v in by_number["NOTIF-2"].vacancies} == {"Post C"}


def test_sync_job_search_index_indexes_a_publicly_visible_job(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session, organization=organization, state=state, source=source, title="Findable Clerk"
    )

    sync_job_search_index(db_session, job)

    result = search_documents(db_session, q="Findable Clerk", locale="en")
    assert result.total_count == 1
    assert result.rows[0].document.entity_type == SEARCH_ENTITY_TYPE
    assert result.rows[0].document.entity_id == job.id


def test_sync_job_search_index_removes_a_job_that_becomes_unpublished(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session, organization=organization, state=state, source=source, title="Findable Clerk"
    )
    sync_job_search_index(db_session, job)
    assert search_documents(db_session, q="Findable Clerk", locale="en").total_count == 1

    job.publication_status = JobPublicationStatus.ARCHIVED
    db_session.flush()
    sync_job_search_index(db_session, job)

    assert search_documents(db_session, q="Findable Clerk", locale="en").total_count == 0
