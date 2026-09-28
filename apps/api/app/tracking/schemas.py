"""Request/response contract for /api/v1/tracking — see docs/API.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.sources.enums import VerificationStatus
from app.tracking.enums import TrackedEntityType


class TrackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: TrackedEntityType
    entity_slug: str = Field(min_length=1, max_length=220)
    label: str | None = Field(default=None, max_length=200)


class UpdateLabelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=200)


class TrackedItemResponse(BaseModel):
    id: uuid.UUID
    entity_type: TrackedEntityType
    title: str | None
    route: str | None
    verification_status: VerificationStatus | None
    last_verified: datetime | None
    source_organization: str | None
    still_available: bool
    label: str | None
    is_active: bool
    created_at: datetime
    deadline: date | None
    deadline_expired: bool | None


class TrackedItemListResponse(BaseModel):
    results: list[TrackedItemResponse]
