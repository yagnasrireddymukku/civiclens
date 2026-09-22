"""Request/response contract for /api/v1/documents — see docs/API.md
§17 for the conventions every field here follows, and
`app/schemes/schemas.py` for the identical pattern this mirrors
(Pydantic validation, explicit enums, provenance-carrying response
shape, standard pagination).

`SourceSummary`/`OrganizationSummary`/`DepartmentSummary`/
`PaginationMeta` are redefined here rather than imported from
`app.schemes.schemas`, for the same reason that module gives for not
importing from `app.services.schemas`: a small, locally-owned
presentational DTO per domain module, not a cross-module import for a
few lines of shape (CLAUDE.md rule 10).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.documents.enums import DocumentCategory, DocumentType
from app.requirements.enums import ApplicationChannelType, DeliveryMode, RequirementType
from app.sources.enums import VerificationStatus

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20


class DocumentListQueryParams(BaseModel):
    """Validated query parameters for `GET /documents`. `sort` is a
    `Literal` with one allowed value today — an explicit allow-list
    (docs/API.md §6), never a popularity-based sort."""

    model_config = ConfigDict(extra="forbid")

    state_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    document_type: DocumentType | None = None
    category: DocumentCategory | None = None
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


class DocumentListItem(BaseModel):
    # `slug`, not a raw database id, is the sole public identifier
    # (docs/API.md §12's "don't expose internal database IDs
    # unnecessarily").
    slug: str
    name: str
    organization: OrganizationSummary
    department: DepartmentSummary | None
    short_description: str | None
    document_type: DocumentType
    category: DocumentCategory
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


class CivicDocumentRefSummary(BaseModel):
    """A small pointer to another `CivicDocument` — used both for a
    supporting document that is itself modeled (§11) and, in reverse,
    nowhere directly (see `RequiredBySummary` for that direction)."""

    slug: str
    name: str


class SupportingDocumentSummary(BaseModel):
    name: str
    description: str | None
    is_mandatory: bool
    # Present only when this supporting document is itself a modeled
    # `CivicDocument` (this phase's §11) — `null` when it's free text
    # only, same convention as every other optional nested reference in
    # this codebase.
    civic_document: CivicDocumentRefSummary | None


class ApplicationMethodSummary(BaseModel):
    channel_type: ApplicationChannelType
    url: str | None
    instructions: str | None


class ServiceRefSummary(BaseModel):
    slug: str
    name: str


class RequiredBySummary(BaseModel):
    """One record that references this document as something a citizen
    needs to provide (this phase's §14/§22) — only ever populated from
    an explicit, modeled `civic_document_id` link, never inferred from
    matching names."""

    entity_type: Literal["service", "scheme"]
    slug: str
    name: str


class DocumentDetail(BaseModel):
    slug: str
    name: str
    organization: OrganizationSummary
    department: DepartmentSummary | None
    short_description: str | None
    description: str | None
    document_type: DocumentType
    category: DocumentCategory
    purpose: str | None
    delivery_mode: DeliveryMode
    state: str | None
    district: str | None
    official_document_url: str | None
    application_url: str | None
    fee_summary: str | None
    processing_time_summary: str | None
    validity_summary: str | None
    renewal_summary: str | None
    status: str | None
    verification_status: VerificationStatus
    last_verified: datetime | None
    source: SourceSummary
    requirements: list[RequirementSummary]
    supporting_documents: list[SupportingDocumentSummary]
    application_methods: list[ApplicationMethodSummary]
    # The "obtained through" relationship (this phase's §13) — `null`
    # when no modeled `Service` exists, or when it exists but isn't
    # itself publicly visible.
    service: ServiceRefSummary | None
    # "Where this document may be required" (this phase's §21/§22).
    required_by: list[RequiredBySummary]


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int


class DocumentListResponse(BaseModel):
    results: list[DocumentListItem]
    pagination: PaginationMeta
