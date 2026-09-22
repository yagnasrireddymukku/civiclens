"""Jobs domain model/relationship/constraint tests. Fixture data is
unambiguously fictional (docs/DATA_GOVERNANCE.md §7, docs/TESTING.md §15).
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.jobs.models import Job, JobNotification, JobVacancy, Organization
from tests.test_jobs._helpers import (
    make_department,
    make_district,
    make_job,
    make_notification,
    make_organization,
    make_source,
    make_state,
    make_vacancy,
)


def test_organization_department_job_notification_vacancy_relationships(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    district = make_district(db_session, state)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    department = make_department(db_session, state, organization=organization)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        department=department,
        district=district,
    )
    notification = make_notification(db_session, job, source)
    vacancy = make_vacancy(db_session, notification)

    db_session.refresh(organization)
    db_session.refresh(job)

    assert job in organization.jobs
    assert job.department is department
    assert job.organization is organization
    assert notification in job.notifications
    assert notification.job is job
    assert vacancy in notification.vacancies
    assert vacancy.job_notification is notification


def test_job_requires_an_existing_organization(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)

    db_session.add(
        Job(
            slug="orphan-job",
            locale="en",
            title="Orphan Job",
            organization_id=uuid.uuid4(),
            employment_type="PERMANENT",
            state_id=state.id,
            publication_status="DRAFT",
            source_id=source.id,
            verification_status="UNVERIFIED",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_job_cannot_be_created_without_a_source(db_session: Session) -> None:
    """The literal Phase 6 acceptance criterion: a job cannot be created
    without a `source_id` (docs/ROADMAP.md Phase 6, ADR-008)."""
    state = make_state(db_session)
    organization = make_organization(db_session, state)

    with pytest.raises(IntegrityError):
        db_session.add(
            Job(
                slug="sourceless-job",
                locale="en",
                title="Sourceless Job",
                organization_id=organization.id,
                employment_type="PERMANENT",
                state_id=state.id,
                publication_status="DRAFT",
                source_id=None,  # type: ignore[arg-type]
                verification_status="UNVERIFIED",
            )
        )
        db_session.flush()


def test_job_slug_must_be_unique(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(db_session, organization=organization, state=state, source=source, slug="dup-slug")

    with pytest.raises(IntegrityError):
        make_job(db_session, organization=organization, state=state, source=source, slug="dup-slug")


def test_department_name_unique_within_organization_but_reusable_across_organizations(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    org_one = make_organization(db_session, state, name="Test Board One — Not Real")
    org_two = make_organization(db_session, state, name="Test Board Two — Not Real")

    make_department(db_session, state, organization=org_one, name="Test Department — Not Real")
    # Same name, different organization — must be allowed.
    make_department(db_session, state, organization=org_two, name="Test Department — Not Real")

    # Same name, same organization — must be rejected.
    with pytest.raises(IntegrityError):
        make_department(db_session, state, organization=org_one, name="Test Department — Not Real")


def test_organization_state_is_nullable_for_national_bodies(db_session: Session) -> None:
    organization = Organization(
        name="Test National Board — Not Real", org_type="CENTRAL", state_id=None
    )
    db_session.add(organization)
    db_session.flush()  # must not raise

    assert organization.state_id is None


def test_deleting_organization_is_restricted_while_jobs_reference_it(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(db_session, organization=organization, state=state, source=source)

    db_session.delete(organization)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_department_sets_job_department_to_null(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    department = make_department(db_session, state, organization=organization)
    job = make_job(
        db_session, organization=organization, state=state, source=source, department=department
    )
    job_id = job.id

    db_session.delete(department)
    db_session.flush()

    db_session.expire_all()
    reloaded_job = db_session.get(Job, job_id)
    assert reloaded_job is not None
    assert reloaded_job.department_id is None


def test_deleting_job_cascades_to_notifications_and_vacancies(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    notification = make_notification(db_session, job, source)
    vacancy = make_vacancy(db_session, notification)
    notification_id, vacancy_id = notification.id, vacancy.id

    db_session.delete(job)
    db_session.flush()

    assert db_session.get(JobNotification, notification_id) is None
    assert db_session.get(JobVacancy, vacancy_id) is None


def test_job_soft_delete_field_defaults_to_none(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)

    assert job.deleted_at is None
