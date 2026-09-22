"""Job domain query/business logic — the only code path that reads
`jobs`/`job_notifications`/`job_vacancies` for the public API, and the
only place that keeps a job's Civic Search projection in sync with its
publication/verification state (docs/SEARCH.md §12, this phase's §16).

Visibility rule, applied identically everywhere a job is read (list,
detail, and the search-index sync below): a job is publicly visible only
when `publication_status == PUBLISHED`, `verification_status` is
`VERIFIED`/`NEEDS_REVIEW` (never `UNVERIFIED`/`EXPIRED`), and it has not
been soft-deleted — this phase's §9 ("a job must never appear publicly
before its required verification/publishing conditions are satisfied").
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.geography.models import District, State
from app.institutions.models import Department, Organization
from app.jobs.enums import EmploymentType, JobPublicationStatus
from app.jobs.models import Job, JobNotification, JobVacancy
from app.search import service as search_service
from app.sources.enums import VerificationStatus
from app.sources.models import Source

SEARCH_ENTITY_TYPE = "job"

# Only these are ever indexed or returned by the public API — matches
# `app.search.service._INDEXABLE_STATUSES` exactly, not by accident:
# both enforce docs/DATA_GOVERNANCE.md §4's four-state model the same
# way.
_PUBLIC_VERIFICATION_STATUSES = (VerificationStatus.VERIFIED, VerificationStatus.NEEDS_REVIEW)


def _visible_predicate() -> Any:
    return and_(
        Job.publication_status == JobPublicationStatus.PUBLISHED,
        Job.verification_status.in_(_PUBLIC_VERIFICATION_STATUSES),
        Job.deleted_at.is_(None),
    )


def is_publicly_visible(job: Job) -> bool:
    return (
        job.publication_status == JobPublicationStatus.PUBLISHED
        and job.verification_status in _PUBLIC_VERIFICATION_STATUSES
        and job.deleted_at is None
    )


def sync_job_search_index(session: Session, job: Job) -> None:
    """Called after a job is created or its publication/verification
    state changes. Indexes it if publicly visible, removes it from the
    index otherwise — never both, and never left stale."""
    if is_publicly_visible(job):
        search_service.upsert_search_document(
            session,
            entity_type=SEARCH_ENTITY_TYPE,
            entity_id=job.id,
            locale=job.locale,
            title=job.title,
            source_id=job.source_id,
            verification_status=job.verification_status,
            summary=job.summary,
            searchable_text=" ".join(
                filter(None, [job.qualification_summary, job.experience_summary, job.category])
            ),
            route=f"/jobs/{job.slug}",
            state_id=job.state_id,
            district_id=job.district_id,
            category=job.category,
            status=job.status,
            last_verified_at=job.last_verified_at,
        )
    else:
        search_service.remove_search_document(
            session, entity_type=SEARCH_ENTITY_TYPE, entity_id=job.id, locale=job.locale
        )


@dataclass
class JobRow:
    job: Job
    organization: Organization
    department: Department | None
    state_name: str
    district_name: str | None
    source: Source


@dataclass
class JobListResult:
    rows: list[JobRow]
    total_count: int


def _base_job_select() -> Select[Any]:
    return (
        select(Job, Organization, Department, State.name, District.name, Source)
        .join(Organization, Job.organization_id == Organization.id)
        .outerjoin(Department, Job.department_id == Department.id)
        .join(State, Job.state_id == State.id)
        .outerjoin(District, Job.district_id == District.id)
        .join(Source, Job.source_id == Source.id)
        .where(_visible_predicate())
    )


def _apply_filters(
    stmt: Select[Any],
    *,
    state_id: uuid.UUID | None,
    district_id: uuid.UUID | None,
    organization_id: uuid.UUID | None,
    department_id: uuid.UUID | None,
    status: str | None,
    employment_type: EmploymentType | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select[Any]:
    if state_id is not None:
        stmt = stmt.where(Job.state_id == state_id)
    if district_id is not None:
        stmt = stmt.where(Job.district_id == district_id)
    if organization_id is not None:
        stmt = stmt.where(Job.organization_id == organization_id)
    if department_id is not None:
        stmt = stmt.where(Job.department_id == department_id)
    if status is not None:
        stmt = stmt.where(Job.status == status)
    if employment_type is not None:
        stmt = stmt.where(Job.employment_type == employment_type)
    if date_from is not None:
        stmt = stmt.where(Job.last_verified_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Job.last_verified_at <= date_to)
    return stmt


def list_jobs(
    session: Session,
    *,
    state_id: uuid.UUID | None = None,
    district_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    status: str | None = None,
    employment_type: EmploymentType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> JobListResult:
    """`sort` isn't a parameter here: "recent" (`last_verified_at` desc,
    nulls last) is the only sort this phase implements (this phase's
    §15 — no popularity/salary/"best job" ranking), so there is nothing
    to branch on yet. A future second sort value would add a parameter,
    not change this signature's meaning."""
    filter_kwargs: dict[str, Any] = dict(
        state_id=state_id,
        district_id=district_id,
        organization_id=organization_id,
        department_id=department_id,
        status=status,
        employment_type=employment_type,
        date_from=date_from,
        date_to=date_to,
    )

    count_stmt = _apply_filters(
        select(func.count()).select_from(Job).where(_visible_predicate()), **filter_kwargs
    )
    total_count = session.scalar(count_stmt) or 0

    row_stmt = _apply_filters(_base_job_select(), **filter_kwargs)
    row_stmt = row_stmt.order_by(Job.last_verified_at.desc().nullslast())
    row_stmt = row_stmt.offset((page - 1) * page_size).limit(page_size)

    rows = [
        JobRow(
            job=job,
            organization=organization,
            department=department,
            state_name=state_name,
            district_name=district_name,
            source=source,
        )
        for job, organization, department, state_name, district_name, source in session.execute(
            row_stmt
        ).all()
    ]
    return JobListResult(rows=rows, total_count=total_count)


@dataclass
class NotificationRow:
    notification: JobNotification
    source: Source
    vacancies: list[JobVacancy]


def get_job_by_slug(session: Session, slug: str) -> JobRow | None:
    """Returns `None` for a job that doesn't exist *or* isn't publicly
    visible — the route layer maps both to an identical 404, never
    distinguishing "not found" from "not yet published" to an
    unauthenticated caller."""
    stmt = _base_job_select().where(Job.slug == slug)
    result = session.execute(stmt).first()
    if result is None:
        return None
    job, organization, department, state_name, district_name, source = result
    return JobRow(
        job=job,
        organization=organization,
        department=department,
        state_name=state_name,
        district_name=district_name,
        source=source,
    )


def list_notifications_for_job(session: Session, job_id: uuid.UUID) -> list[NotificationRow]:
    """Two bounded queries regardless of how many notifications/vacancies
    exist (this phase's §29 — no N+1): one for notifications + their
    source, one for every vacancy across all of them, grouped in Python."""
    notification_stmt = (
        select(JobNotification, Source)
        .join(Source, JobNotification.source_id == Source.id)
        .where(JobNotification.job_id == job_id)
        .order_by(JobNotification.created_at)
    )
    notification_rows = session.execute(notification_stmt).all()
    notification_ids = [notification.id for notification, _ in notification_rows]

    vacancies_by_notification: dict[uuid.UUID, list[JobVacancy]] = {
        notification_id: [] for notification_id in notification_ids
    }
    if notification_ids:
        vacancy_stmt = select(JobVacancy).where(
            JobVacancy.job_notification_id.in_(notification_ids)
        )
        for vacancy in session.scalars(vacancy_stmt):
            vacancies_by_notification[vacancy.job_notification_id].append(vacancy)

    return [
        NotificationRow(
            notification=notification,
            source=source,
            vacancies=vacancies_by_notification[notification.id],
        )
        for notification, source in notification_rows
    ]
