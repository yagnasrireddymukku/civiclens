"""GET/POST /api/v1/tracking, PATCH/DELETE /api/v1/tracking/{id},
POST /api/v1/tracking/{id}/pause, /resume — see docs/API.md.

Every route sits behind `get_current_user` — there is no public read or
write path onto another user's tracked items (this phase's explicit
"never a public endpoint that lets unauthenticated users create or
read arbitrary user tracking data"). State-changing routes also require
`verify_csrf`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, verify_csrf
from app.core.db.session import get_db
from app.tracking import service
from app.tracking.deadlines import get_deadline_for_entity, is_expired
from app.tracking.schemas import (
    TrackedItemListResponse,
    TrackedItemResponse,
    TrackRequest,
    UpdateLabelRequest,
)
from app.users.models import User

router = APIRouter(prefix="/tracking", tags=["tracking"])


def _to_response(session: Session, view: service.TrackedItemView) -> TrackedItemResponse:
    deadline = get_deadline_for_entity(session, view.entity_type, view.entity_id)
    now = datetime.now(UTC)
    return TrackedItemResponse(
        id=view.tracked_item.id,
        entity_type=view.entity_type,
        title=view.title,
        route=view.route,
        verification_status=view.verification_status,
        last_verified=view.last_verified_at,
        source_organization=view.source_organization,
        still_available=view.still_available,
        label=view.tracked_item.label,
        is_active=view.tracked_item.is_active,
        created_at=view.tracked_item.created_at,
        deadline=deadline,
        deadline_expired=is_expired(deadline, now=now) if deadline is not None else None,
    )


@router.get("", response_model=TrackedItemListResponse)
def list_tracked_items(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> TrackedItemListResponse:
    views = service.list_tracked_items(db, user_id=current_user.id)
    return TrackedItemListResponse(results=[_to_response(db, view) for view in views])


@router.post(
    "",
    response_model=TrackedItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def track(
    payload: TrackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrackedItemResponse:
    entity = service.resolve_entity(db, payload.entity_type, payload.entity_slug)
    if entity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entity not found")

    item = service.track_entity(
        db, user_id=current_user.id, entity_type=entity.entity_type, entity_id=entity.entity_id
    )
    if payload.label is not None:
        item.label = payload.label
    db.flush()

    views = service.list_tracked_items(db, user_id=current_user.id)
    view = next(v for v in views if v.tracked_item.id == item.id)
    return _to_response(db, view)


@router.patch(
    "/{tracked_item_id}", response_model=TrackedItemResponse, dependencies=[Depends(verify_csrf)]
)
def update_label(
    tracked_item_id: uuid.UUID,
    payload: UpdateLabelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrackedItemResponse:
    try:
        service.update_label(
            db, user_id=current_user.id, tracked_item_id=tracked_item_id, label=payload.label
        )
    except service.TrackedItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tracked item not found") from exc
    db.flush()

    views = service.list_tracked_items(db, user_id=current_user.id)
    view = next(v for v in views if v.tracked_item.id == tracked_item_id)
    return _to_response(db, view)


@router.post(
    "/{tracked_item_id}/pause",
    response_model=TrackedItemResponse,
    dependencies=[Depends(verify_csrf)],
)
def pause(
    tracked_item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrackedItemResponse:
    try:
        service.pause_tracked_item(db, user_id=current_user.id, tracked_item_id=tracked_item_id)
    except service.TrackedItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tracked item not found") from exc
    db.flush()

    views = service.list_tracked_items(db, user_id=current_user.id)
    view = next(v for v in views if v.tracked_item.id == tracked_item_id)
    return _to_response(db, view)


@router.post(
    "/{tracked_item_id}/resume",
    response_model=TrackedItemResponse,
    dependencies=[Depends(verify_csrf)],
)
def resume(
    tracked_item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrackedItemResponse:
    try:
        service.resume_tracked_item(db, user_id=current_user.id, tracked_item_id=tracked_item_id)
    except service.TrackedItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tracked item not found") from exc
    db.flush()

    views = service.list_tracked_items(db, user_id=current_user.id)
    view = next(v for v in views if v.tracked_item.id == tracked_item_id)
    return _to_response(db, view)


@router.delete(
    "/{tracked_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
def untrack(
    tracked_item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        service.remove_tracked_item(db, user_id=current_user.id, tracked_item_id=tracked_item_id)
    except service.TrackedItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tracked item not found") from exc
