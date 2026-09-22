"""Request/response contract for /api/v1/schemes — see docs/API.md §15
for the conventions every field here follows, and `app/services/schemas.py`
for the identical pattern this mirrors (Pydantic validation, explicit
enums, provenance-carrying response shape, standard pagination).

`SourceSummary`/`OrganizationSummary`/`DepartmentSummary`/
`PaginationMeta` are redefined here rather than imported from
`app.services.schemas`, for the same reason that module gives for not
importing from `app.jobs.schemas`: a small, locally-owned presentational
DTO per domain module, not a cross-module import for a few lines of
shape (CLAUDE.md rule 10).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.requirements.enums import ApplicationChannelType, RequirementType
from app.schemes.enums import BenefitType, EducationLevel, SchemeCategory, StudyMode
from app.sources.enums import VerificationStatus

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20


class SchemeListQueryParams(BaseModel):
    """Validated query parameters for `GET /schemes`. `sort` is a
    `Literal` with one allowed value today — an explicit allow-list
    (docs/API.md §6), never a popularity-based sort."""

    model_config = ConfigDict(extra="forbid")

    state_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    category: SchemeCategory | None = None
    # Phase 9: filters on `ScholarshipDetail.education_level` — only
    # matches schemes that have a scholarship detail row at all, so
    # combining this with a non-scholarship `category` deliberately
    # yields zero results rather than silently ignoring one filter.
    education_level: EducationLevel | None = None
    status: str | None = Field(default=None, max_length=50)
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


class SchemeListItem(BaseModel):
    # `slug`, not a raw database id, is the sole public identifier
    # (this phase's §21; docs/API.md §12's "don't expose internal
    # database IDs unnecessarily").
    slug: str
    name: str
    organization: OrganizationSummary
    department: DepartmentSummary | None
    short_description: str | None
    category: SchemeCategory
    state: str | None
    district: str | None
    status: str | None
    verification_status: VerificationStatus
    last_verified: datetime | None
    source: SourceSummary


class BenefitSummary(BaseModel):
    benefit_type: BenefitType
    description: str
    amount_summary: str | None
    frequency_summary: str | None


class RequirementSummary(BaseModel):
    requirement_type: RequirementType
    description: str
    min_value: int | None
    max_value: int | None


class RequiredDocumentSummary(BaseModel):
    name: str
    description: str | None
    is_mandatory: bool


class ApplicationMethodSummary(BaseModel):
    channel_type: ApplicationChannelType
    url: str | None
    instructions: str | None


class RelatedServiceSummary(BaseModel):
    slug: str
    name: str
    note: str | None


class ScholarshipDetailSummary(BaseModel):
    """Present only when the scheme has a `ScholarshipDetail` row
    (Phase 9, docs/DATABASE.md §13) — `null` on `SchemeDetail.scholarship`
    for every non-scholarship scheme, not an object of all-`null` fields."""

    education_level: EducationLevel | None
    course_discipline: str | None
    institution_type: str | None
    study_mode: StudyMode | None
    year_of_study: str | None
    minimum_percentage: Decimal | None
    minimum_cgpa: Decimal | None
    academic_requirement_notes: str | None
    application_opens: date | None
    application_closes: date | None
    correction_window_end: date | None
    academic_year: str | None
    renewable: bool
    renewal_notes: str | None


class SchemeDetail(BaseModel):
    slug: str
    name: str
    organization: OrganizationSummary
    department: DepartmentSummary | None
    short_description: str | None
    description: str | None
    category: SchemeCategory
    target_audience: str | None
    state: str | None
    district: str | None
    official_scheme_url: str | None
    application_url: str | None
    status: str | None
    verification_status: VerificationStatus
    last_verified: datetime | None
    source: SourceSummary
    benefits: list[BenefitSummary]
    requirements: list[RequirementSummary]
    required_documents: list[RequiredDocumentSummary]
    application_methods: list[ApplicationMethodSummary]
    related_services: list[RelatedServiceSummary]
    scholarship: ScholarshipDetailSummary | None


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int


class SchemeListResponse(BaseModel):
    results: list[SchemeListItem]
    pagination: PaginationMeta
