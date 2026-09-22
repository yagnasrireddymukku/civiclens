"""Shared fixture-building helpers for Jobs domain tests — plain
functions, not pytest fixtures, mirroring
tests/test_search/test_service.py's `make_source`/`index_document`
pattern. Fixture data is unambiguously fictional
(docs/DATA_GOVERNANCE.md §7, docs/TESTING.md §15).
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.geography.enums import StateStatus
from app.geography.models import District, State
from app.jobs.enums import (
    EmploymentType,
    JobNotificationStatus,
    JobPublicationStatus,
    OrganizationType,
)
from app.jobs.models import Department, Job, JobNotification, JobVacancy, Organization
from app.sources.enums import VerificationStatus
from app.sources.models import Source


def make_state(session: Session, **overrides: Any) -> State:
    defaults: dict[str, Any] = dict(
        name="Testland", code="ZZ", slug="testland", status=StateStatus.PLANNED
    )
    defaults.update(overrides)
    state = State(**defaults)
    session.add(state)
    session.flush()
    return state


def make_district(session: Session, state: State, **overrides: Any) -> District:
    defaults: dict[str, Any] = dict(
        state_id=state.id, name="Sampleburg", code="SB", slug="sampleburg"
    )
    defaults.update(overrides)
    district = District(**defaults)
    session.add(district)
    session.flush()
    return district


def make_source(session: Session, **overrides: Any) -> Source:
    defaults: dict[str, Any] = dict(
        url="https://example-test.invalid/notice/jobs",
        title="Test Notice — Not Real",
        organization="Test Recruitment Board — Not Real",
        source_type="test-fixture",
        retrieved_date=datetime.date(2026, 1, 1),
    )
    defaults.update(overrides)
    source = Source(**defaults)
    session.add(source)
    session.flush()
    return source


def make_organization(session: Session, state: State, **overrides: Any) -> Organization:
    defaults: dict[str, Any] = dict(
        name="Test Recruitment Board — Not Real",
        org_type=OrganizationType.AUTONOMOUS_BODY,
        state_id=state.id,
    )
    defaults.update(overrides)
    organization = Organization(**defaults)
    session.add(organization)
    session.flush()
    return organization


def make_department(
    session: Session, state: State, organization: Organization | None = None, **overrides: Any
) -> Department:
    defaults: dict[str, Any] = dict(
        name="Test Department — Not Real",
        organization_id=organization.id if organization else None,
        state_id=state.id,
    )
    defaults.update(overrides)
    department = Department(**defaults)
    session.add(department)
    session.flush()
    return department


def make_job(
    session: Session,
    *,
    organization: Organization,
    state: State,
    source: Source,
    department: Department | None = None,
    district: District | None = None,
    **overrides: Any,
) -> Job:
    defaults: dict[str, Any] = dict(
        slug=f"test-job-{uuid.uuid4().hex[:8]}",
        locale="en",
        title="Test Civic Clerk Recruitment (Fixture)",
        organization_id=organization.id,
        department_id=department.id if department else None,
        summary="A fictional job used only to exercise the jobs domain.",
        description=None,
        employment_type=EmploymentType.PERMANENT,
        category="clerical",
        state_id=state.id,
        district_id=district.id if district else None,
        min_age=None,
        max_age=None,
        qualification_summary=None,
        experience_summary=None,
        salary_summary=None,
        status="open",
        publication_status=JobPublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    defaults.update(overrides)
    job = Job(**defaults)
    session.add(job)
    session.flush()
    return job


def make_notification(
    session: Session, job: Job, source: Source, **overrides: Any
) -> JobNotification:
    defaults: dict[str, Any] = dict(
        job_id=job.id,
        notification_number="TEST_CIVICLENS_JOB_001",
        status=JobNotificationStatus.APPLICATION_OPEN,
        published_date=datetime.date(2026, 7, 1),
        application_start=datetime.date(2026, 7, 15),
        application_end=datetime.date(2026, 8, 15),
        correction_window_end=None,
        exam_date=None,
        total_vacancies=10,
        official_notification_url="https://example-test.invalid/notice/test-job",
        official_application_url="https://example-test.invalid/apply/test-job",
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    defaults.update(overrides)
    notification = JobNotification(**defaults)
    session.add(notification)
    session.flush()
    return notification


def make_vacancy(session: Session, notification: JobNotification, **overrides: Any) -> JobVacancy:
    defaults: dict[str, Any] = dict(
        job_notification_id=notification.id,
        post_name="Junior Clerk (Fixture)",
        vacancy_count=5,
        category=None,
        location="Sampleburg",
    )
    defaults.update(overrides)
    vacancy = JobVacancy(**defaults)
    session.add(vacancy)
    session.flush()
    return vacancy
