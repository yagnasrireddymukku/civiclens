"""Request/response contract for /api/v1/admin — see docs/API.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.admin.enums import AdminEntityType
from app.sources.enums import ChangeReviewStatus, VerificationStatus


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int


class EntityDisplaySummary(BaseModel):
    title: str | None
    route: str | None
    verification_status: VerificationStatus | None
    source_organization: str | None


class ChangeRecordResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    field: str
    old_value: str | None
    new_value: str | None
    detected_at: datetime
    review_status: ChangeReviewStatus
    reviewed_by: uuid.UUID | None
    applied_at: datetime | None
    entity: EntityDisplaySummary


class ChangeRecordListResponse(BaseModel):
    results: list[ChangeRecordResponse]
    pagination: PaginationMeta


class VerificationQueueItem(BaseModel):
    entity_type: AdminEntityType
    entity_id: uuid.UUID
    title: str
    route: str
    verification_status: VerificationStatus
    last_verified: datetime | None
    source_organization: str | None


class VerificationQueueResponse(BaseModel):
    results: list[VerificationQueueItem]
    pagination: PaginationMeta


class SubmitVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: VerificationStatus
    # Required evidence, not optional — mirrors
    # `VerificationRecord.source_id`'s own `nullable=False` (this
    # phase's explicit "no approval without evidence").
    source_id: uuid.UUID
    review_due_at: datetime | None = None


class VerificationRecordResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    source_id: uuid.UUID
    status: VerificationStatus
    verified_by: uuid.UUID | None
    verified_at: datetime | None
    review_due_at: datetime | None


class SourceSummary(BaseModel):
    id: uuid.UUID
    url: str
    title: str
    organization: str
    source_type: str
    published_date: date | None
    retrieved_date: date
    version_count: int


class SourceListResponse(BaseModel):
    results: list[SourceSummary]
    pagination: PaginationMeta


class SourceVersionSummary(BaseModel):
    id: uuid.UUID
    content_hash: str
    snapshot_ref: str | None
    captured_at: datetime


class SourceDetailResponse(BaseModel):
    id: uuid.UUID
    url: str
    title: str
    organization: str
    source_type: str
    published_date: date | None
    retrieved_date: date
    versions: list[SourceVersionSummary]


class RecentChangeDecision(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    field: str
    review_status: ChangeReviewStatus
    reviewed_by: uuid.UUID | None
    applied_at: datetime | None


class RecentVerification(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    status: VerificationStatus
    verified_by: uuid.UUID | None
    verified_at: datetime | None


class DashboardResponse(BaseModel):
    pending_change_records: int
    verification_status_counts: dict[VerificationStatus, int]
    recent_change_decisions: list[RecentChangeDecision]
    recent_verifications: list[RecentVerification]


class ChangeRecordQueryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_status: ChangeReviewStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)


class VerificationQueueQueryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: AdminEntityType | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)


class PageQueryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)
