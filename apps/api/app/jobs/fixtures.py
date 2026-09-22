"""Synthetic Job fixtures — for local development and automated tests
only. Never real government data (docs/DATA_GOVERNANCE.md §7, this
phase's §25).

Naming follows docs/TESTING.md §15 / this phase's §25 exactly: fake
state code "ZZ"/state name "Testland" (reused from
`app.search.fixtures`'s convention), organization "Test Recruitment
Board — Not Real", department "Test Department — Not Real",
notification number "TEST_CIVICLENS_JOB_001", `.invalid` source URLs.
`load_fixtures` refuses to run outside local/test environments — the
same second line of defense `app.search.fixtures.load_fixtures` uses.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.geography.enums import StateStatus
from app.geography.models import District, State
from app.jobs.enums import (
    EmploymentType,
    JobNotificationStatus,
    JobPublicationStatus,
    OrganizationType,
)
from app.jobs.models import Department, Job, JobNotification, JobVacancy, Organization
from app.jobs.service import sync_job_search_index
from app.sources.enums import VerificationStatus
from app.sources.models import Source

_ALLOWED_ENVIRONMENTS = ("local", "test")


def _fixture_state(session: Session) -> State:
    # get-or-create: docs/TESTING.md §15's "ZZ"/"Testland" is the one
    # canonical fictional state every domain's fixtures share, not a
    # value each module recreates — verified by hand that seeding both
    # search and job fixtures into the same database previously failed
    # with a duplicate-state-code error when each blindly inserted it
    # (see app/search/fixtures.py's matching fix).
    existing = session.query(State).filter_by(code="ZZ").one_or_none()
    if existing is not None:
        return existing
    state = State(name="Testland", code="ZZ", slug="testland", status=StateStatus.PLANNED)
    session.add(state)
    session.flush()
    return state


def _fixture_district(session: Session, state: State) -> District:
    existing = session.query(District).filter_by(state_id=state.id, code="SB").one_or_none()
    if existing is not None:
        return existing
    district = District(state_id=state.id, name="Sampleburg", code="SB", slug="sampleburg")
    session.add(district)
    session.flush()
    return district


def _fixture_source() -> Source:
    return Source(
        url="https://example-test.invalid/notice/jobs-fixtures",
        title="Test Notice — Not Real",
        organization="Test Recruitment Board — Not Real",
        source_type="test-fixture",
        retrieved_date=datetime.date(2026, 1, 1),
    )


def load_fixtures(session: Session) -> None:
    """Inserts one small, fixed, clearly-fictional job with one
    notification and two vacancies, then indexes it into Civic Search —
    exercising the full Job -> JobNotification -> JobVacancy ->
    search_documents pipeline end to end. Refuses to run unless
    `APP_ENV` is "local" or "test" — see module docstring.
    """
    settings = get_settings()
    if settings.app_env not in _ALLOWED_ENVIRONMENTS:
        raise RuntimeError(
            f"Refusing to load job fixtures: APP_ENV={settings.app_env!r} is not one of "
            f"{_ALLOWED_ENVIRONMENTS}. Fixtures must never reach a staging/production database."
        )

    state = _fixture_state(session)
    district = _fixture_district(session, state)

    source = _fixture_source()
    session.add(source)
    session.flush()

    organization = Organization(
        name="Test Recruitment Board — Not Real",
        org_type=OrganizationType.AUTONOMOUS_BODY,
        state_id=state.id,
    )
    session.add(organization)

    department = Department(
        name="Test Department — Not Real", organization_id=None, state_id=state.id
    )
    session.add(department)
    session.flush()

    last_verified_at = datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC)

    job = Job(
        slug="test-civiclens-job-001",
        locale="en",
        title="Test Civic Clerk Recruitment (Fixture)",
        organization_id=organization.id,
        department_id=department.id,
        summary="A fictional clerk recruitment notice used only to exercise the jobs domain.",
        description=(
            "This is a synthetic fixture (docs/DATA_GOVERNANCE.md §7) — not a real government "
            "recruitment notice. It exists only to exercise the CivicLens Jobs domain end to end."
        ),
        employment_type=EmploymentType.PERMANENT,
        category="clerical",
        state_id=state.id,
        district_id=district.id,
        min_age=18,
        max_age=44,
        qualification_summary="Bachelor's degree from a recognized university (fictional fixture).",
        experience_summary=None,
        salary_summary=None,
        status="open",
        publication_status=JobPublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=last_verified_at,
    )
    session.add(job)
    session.flush()

    notification = JobNotification(
        job_id=job.id,
        notification_number="TEST_CIVICLENS_JOB_001",
        status=JobNotificationStatus.APPLICATION_OPEN,
        published_date=datetime.date(2026, 7, 1),
        application_start=datetime.date(2026, 7, 15),
        application_end=datetime.date(2026, 8, 15),
        correction_window_end=datetime.date(2026, 8, 20),
        exam_date=None,
        total_vacancies=10,
        official_notification_url="https://example-test.invalid/notice/test-civiclens-job-001",
        official_application_url="https://example-test.invalid/apply/test-civiclens-job-001",
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=last_verified_at,
    )
    session.add(notification)
    session.flush()

    session.add_all(
        [
            JobVacancy(
                job_notification_id=notification.id,
                post_name="Junior Clerk (Fixture)",
                vacancy_count=7,
                category=None,
                location="Sampleburg",
            ),
            JobVacancy(
                job_notification_id=notification.id,
                post_name="Senior Clerk (Fixture)",
                vacancy_count=3,
                category=None,
                location="Sampleburg",
            ),
        ]
    )

    sync_job_search_index(session, job)
    session.commit()
