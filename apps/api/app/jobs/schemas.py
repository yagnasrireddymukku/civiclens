"""Request/response contract for /api/v1/jobs — see docs/API.md §5-9 for
the conventions every field here follows (Pydantic validation, explicit
enums, provenance-carrying response shape, standard pagination).

`SourceSummary`/`PaginationMeta` are deliberately redefined here rather
than imported from `app.search.schemas`, matching that module's own
precedent of a small, locally-owned presentational DTO per domain module
— avoids a cross-module import for four lines of shape, at the cost of
one tiny duplication (CLAUDE.md rule 10: no reach-around into another
domain's internals).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.jobs.enums import EmploymentType, JobNotificationStatus
from app.sources.enums import VerificationStatus

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20


class JobListQueryParams(BaseModel):
    """Validated query parameters for `GET /jobs`. `sort` is a `Literal`
    with one allowed value today — an explicit allow-list (docs/API.md
    §6), never an arbitrary or popularity-based sort (this phase's §15).
    """

    model_config = ConfigDict(extra="forbid")

    state_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    status: str | None = Field(default=None, max_length=50)
    employment_type: EmploymentType | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    sort: Literal["recent"] = "recent"


class SourceSummary(BaseModel):
    organization: str
    title: str
    url: str


class OrganizationSummary(BaseModel):
    name: str
    org_type: str


class DepartmentSummary(BaseModel):
    name: str


class JobListItem(BaseModel):
    # `slug`, not a raw database id, is the sole public identifier
    # (this phase's §24; docs/API.md §12's "don't expose internal
    # database IDs unnecessarily").
    slug: str
    title: str
    organization: OrganizationSummary
    department: DepartmentSummary | None
    summary: str | None
    employment_type: EmploymentType
    category: str | None
    state: str
    district: str | None
    status: str | None
    verification_status: VerificationStatus
    last_verified: datetime | None
    source: SourceSummary


class VacancySummary(BaseModel):
    post_name: str
    vacancy_count: int | None
    category: str | None
    location: str | None


class NotificationSummary(BaseModel):
    notification_number: str | None
    status: JobNotificationStatus
    published_date: date | None
    application_start: date | None
    application_end: date | None
    correction_window_end: date | None
    exam_date: date | None
    total_vacancies: int | None
    official_notification_url: str | None
    official_application_url: str | None
    verification_status: VerificationStatus
    last_verified: datetime | None
    source: SourceSummary
    vacancies: list[VacancySummary]


class JobDetail(BaseModel):
    slug: str
    title: str
    organization: OrganizationSummary
    department: DepartmentSummary | None
    summary: str | None
    description: str | None
    employment_type: EmploymentType
    category: str | None
    state: str
    district: str | None
    min_age: int | None
    max_age: int | None
    qualification_summary: str | None
    experience_summary: str | None
    salary_summary: str | None
    status: str | None
    verification_status: VerificationStatus
    last_verified: datetime | None
    source: SourceSummary
    # Ordered oldest-first (matches `Job.notifications`'s relationship
    # ordering) so the most recent recruitment cycle is last/most visible
    # in a naturally-scrolling detail page.
    notifications: list[NotificationSummary]


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int


class JobListResponse(BaseModel):
    results: list[JobListItem]
    pagination: PaginationMeta
