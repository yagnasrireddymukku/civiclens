"""Request/response contract for /api/v1/services — see docs/API.md §14
for the conventions every field here follows, and `app/jobs/schemas.py`
for the identical pattern this mirrors (Pydantic validation, explicit
enums, provenance-carrying response shape, standard pagination).

`SourceSummary`/`OrganizationSummary`/`DepartmentSummary`/
`PaginationMeta` are redefined here rather than imported from
`app.jobs.schemas`, for the same reason that module gives for not
importing from `app.search.schemas`: a small, locally-owned
presentational DTO per domain module, not a cross-module import for a
few lines of shape (CLAUDE.md rule 10).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.enums import (
    ApplicationChannelType,
    DeliveryMode,
    RequirementType,
    ServiceCategory,
)
from app.sources.enums import VerificationStatus

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20


class ServiceListQueryParams(BaseModel):
    """Validated query parameters for `GET /services`. `sort` is a
    `Literal` with one allowed value today — an explicit allow-list
    (docs/API.md §6), never a popularity-based sort."""

    model_config = ConfigDict(extra="forbid")

    state_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    category: ServiceCategory | None = None
    delivery_mode: DeliveryMode | None = None
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


class ServiceListItem(BaseModel):
    # `slug`, not a raw database id, is the sole public identifier
    # (this phase's §21; docs/API.md §12's "don't expose internal
    # database IDs unnecessarily").
    slug: str
    name: str
    organization: OrganizationSummary
    department: DepartmentSummary | None
    short_description: str | None
    category: ServiceCategory
    service_type: str | None
    delivery_mode: DeliveryMode
    state: str | None
    district: str | None
    status: str | None
    verification_status: VerificationStatus
    last_verified: datetime | None
    source: SourceSummary


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


class ServiceDetail(BaseModel):
    slug: str
    name: str
    organization: OrganizationSummary
    department: DepartmentSummary | None
    short_description: str | None
    description: str | None
    category: ServiceCategory
    service_type: str | None
    target_audience: str | None
    delivery_mode: DeliveryMode
    state: str | None
    district: str | None
    official_service_url: str | None
    application_url: str | None
    fee_summary: str | None
    processing_time_summary: str | None
    location_summary: str | None
    status: str | None
    verification_status: VerificationStatus
    last_verified: datetime | None
    source: SourceSummary
    requirements: list[RequirementSummary]
    required_documents: list[RequiredDocumentSummary]
    application_methods: list[ApplicationMethodSummary]


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int


class ServiceListResponse(BaseModel):
    results: list[ServiceListItem]
    pagination: PaginationMeta
