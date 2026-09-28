"""GET /api/v1/notifications, POST /api/v1/notifications/{id}/read,
POST /api/v1/notifications/read-all — see docs/API.md.

Every route sits behind `get_current_user` — no public read path onto
another user's notifications (this phase's explicit ownership
requirement, mirroring `app.api.v1.tracking`'s identical convention).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, verify_csrf
from app.core.db.session import get_db
from app.notifications import service
from app.notifications.models import Notification
from app.notifications.schemas import (
    NotificationListQueryParams,
    NotificationListResponse,
    NotificationResponse,
    PaginationMeta,
)
from app.users.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        notification_type=notification.notification_type,
        title=notification.title,
        body=notification.body,
        entity_type=notification.entity_type,
        entity_id=notification.entity_id,
        created_at=notification.created_at,
        read_at=notification.read_at,
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    params: Annotated[NotificationListQueryParams, Query()],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    result = service.list_notifications(
        db, user_id=current_user.id, page=params.page, page_size=params.page_size
    )
    return NotificationListResponse(
        results=[_to_response(n) for n in result.rows],
        pagination=PaginationMeta(
            page=params.page, page_size=params.page_size, total_count=result.total_count
        ),
        unread_count=result.unread_count,
    )


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    dependencies=[Depends(verify_csrf)],
)
def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    try:
        notification = service.mark_read(
            db, user_id=current_user.id, notification_id=notification_id
        )
    except service.NotificationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found") from exc
    db.flush()
    return _to_response(notification)


@router.post(
    "/read-all", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)]
)
def mark_all_read(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    service.mark_all_read(db, user_id=current_user.id)
