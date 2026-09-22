"""GET /api/v1/jobs, GET /api/v1/jobs/{slug} — see docs/API.md §6 for the
pagination/filtering conventions and docs/DATABASE.md §2.3/§8 for the
underlying schema. Route handlers here only translate between HTTP and
`app.jobs.service` plus map ORM rows to response schemas — no query
logic lives in this file.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.jobs import service
from app.jobs.schemas import (
    DepartmentSummary,
    JobDetail,
    JobListItem,
    JobListQueryParams,
    JobListResponse,
    NotificationSummary,
    OrganizationSummary,
    PaginationMeta,
    SourceSummary,
    VacancySummary,
)
from app.jobs.service import JobRow, NotificationRow

router = APIRouter(tags=["jobs"])


def _job_list_item(row: JobRow) -> JobListItem:
    job = row.job
    return JobListItem(
        slug=job.slug,
        title=job.title,
        organization=OrganizationSummary(
            name=row.organization.name, org_type=row.organization.org_type.value
        ),
        department=DepartmentSummary(name=row.department.name) if row.department else None,
        summary=job.summary,
        employment_type=job.employment_type,
        category=job.category,
        state=row.state_name,
        district=row.district_name,
        status=job.status,
        verification_status=job.verification_status,
        last_verified=job.last_verified_at,
        source=SourceSummary(
            organization=row.source.organization, title=row.source.title, url=row.source.url
        ),
    )


def _notification_summary(row: NotificationRow) -> NotificationSummary:
    notification = row.notification
    return NotificationSummary(
        notification_number=notification.notification_number,
        status=notification.status,
        published_date=notification.published_date,
        application_start=notification.application_start,
        application_end=notification.application_end,
        correction_window_end=notification.correction_window_end,
        exam_date=notification.exam_date,
        total_vacancies=notification.total_vacancies,
        official_notification_url=notification.official_notification_url,
        official_application_url=notification.official_application_url,
        verification_status=notification.verification_status,
        last_verified=notification.last_verified_at,
        source=SourceSummary(
            organization=row.source.organization, title=row.source.title, url=row.source.url
        ),
        vacancies=[
            VacancySummary(
                post_name=vacancy.post_name,
                vacancy_count=vacancy.vacancy_count,
                category=vacancy.category,
                location=vacancy.location,
            )
            for vacancy in row.vacancies
        ],
    )


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    params: Annotated[JobListQueryParams, Query()],
    db: Session = Depends(get_db),
) -> JobListResponse:
    result = service.list_jobs(
        db,
        state_id=params.state_id,
        district_id=params.district_id,
        organization_id=params.organization_id,
        department_id=params.department_id,
        status=params.status,
        employment_type=params.employment_type,
        date_from=params.date_from,
        date_to=params.date_to,
        page=params.page,
        page_size=params.page_size,
    )
    return JobListResponse(
        results=[_job_list_item(row) for row in result.rows],
        pagination=PaginationMeta(
            page=params.page, page_size=params.page_size, total_count=result.total_count
        ),
    )


@router.get("/jobs/{slug}", response_model=JobDetail)
def get_job(slug: str, db: Session = Depends(get_db)) -> JobDetail:
    row = service.get_job_by_slug(db, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    job = row.job
    notifications = service.list_notifications_for_job(db, job.id)

    return JobDetail(
        slug=job.slug,
        title=job.title,
        organization=OrganizationSummary(
            name=row.organization.name, org_type=row.organization.org_type.value
        ),
        department=DepartmentSummary(name=row.department.name) if row.department else None,
        summary=job.summary,
        description=job.description,
        employment_type=job.employment_type,
        category=job.category,
        state=row.state_name,
        district=row.district_name,
        min_age=job.min_age,
        max_age=job.max_age,
        qualification_summary=job.qualification_summary,
        experience_summary=job.experience_summary,
        salary_summary=job.salary_summary,
        status=job.status,
        verification_status=job.verification_status,
        last_verified=job.last_verified_at,
        source=SourceSummary(
            organization=row.source.organization, title=row.source.title, url=row.source.url
        ),
        notifications=[
            _notification_summary(notification_row) for notification_row in notifications
        ],
    )
