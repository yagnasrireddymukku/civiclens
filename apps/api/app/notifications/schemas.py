"""Request/response contract for /api/v1/notifications — see docs/API.md."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.notifications.enums import NotificationType

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20


class NotificationListQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)


class NotificationResponse(BaseModel):
    id: uuid.UUID
    notification_type: NotificationType
    title: str
    body: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    created_at: datetime
    read_at: datetime | None


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int


class NotificationListResponse(BaseModel):
    results: list[NotificationResponse]
    pagination: PaginationMeta
    unread_count: int
