"""GET/POST /api/v1/admin/* — the Admin Intelligence Center review
console. See docs/API.md §21 and `app.admin.service`'s module
docstring for this phase's scope (review/approval of already-detected
changes and entity verification, not a live ingestion pipeline).

Every route sits behind `require_role(EDITOR, ADMIN)` — an ordinary
authenticated `user` gets a 403, never a 404 (there is no per-object
ownership to hide here, unlike `app.api.v1.tracking`/`notifications`;
this is a role check, not an IDOR-safety concern). Every mutating route
additionally requires CSRF and is rate-limited
(`app.admin.rate_limit.enforce_admin_rate_limit`).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.admin import service
from app.admin.enums import AdminEntityType
from app.admin.rate_limit import enforce_admin_rate_limit
from app.admin.schemas import (
    ChangeRecordListResponse,
    ChangeRecordQueryParams,
    ChangeRecordResponse,
    DashboardResponse,
    EntityDisplaySummary,
    PageQueryParams,
    PaginationMeta,
    RecentChangeDecision,
    RecentVerification,
    SourceDetailResponse,
    SourceListResponse,
    SourceSummary,
    SourceVersionSummary,
    SubmitVerificationRequest,
    VerificationQueueItem,
    VerificationQueueQueryParams,
    VerificationQueueResponse,
    VerificationRecordResponse,
)
from app.auth.dependencies import require_role, verify_csrf
from app.core.db.session import get_db
from app.users.enums import UserRole
from app.users.models import User

router = APIRouter(prefix="/admin", tags=["admin"])

_require_reviewer = require_role(UserRole.EDITOR, UserRole.ADMIN)


def _change_record_response(entry: service.ChangeRecordEntry) -> ChangeRecordResponse:
    record = entry.record
    return ChangeRecordResponse(
        id=record.id,
        entity_type=record.entity_type,
        entity_id=record.entity_id,
        field=record.field,
        old_value=record.old_value,
        new_value=record.new_value,
        detected_at=record.detected_at,
        review_status=record.review_status,
        reviewed_by=record.reviewed_by,
        applied_at=record.applied_at,
        entity=EntityDisplaySummary(
            title=entry.display.title,
            route=entry.display.route,
            verification_status=entry.display.verification_status,
            source_organization=entry.display.source_organization,
        ),
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(_require_reviewer), db: Session = Depends(get_db)
) -> DashboardResponse:
    metrics = service.get_dashboard_metrics(db)
    return DashboardResponse(
        pending_change_records=metrics.pending_change_records,
        verification_status_counts=metrics.verification_status_counts,
        recent_change_decisions=[
            RecentChangeDecision(
                id=r.id,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                field=r.field,
                review_status=r.review_status,
                reviewed_by=r.reviewed_by,
                applied_at=r.applied_at,
            )
            for r in metrics.recent_change_decisions
        ],
        recent_verifications=[
            RecentVerification(
                id=r.id,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                status=r.status,
                verified_by=r.verified_by,
                verified_at=r.verified_at,
            )
            for r in metrics.recent_verifications
        ],
    )


@router.get("/change-records", response_model=ChangeRecordListResponse)
def list_change_records(
    params: Annotated[ChangeRecordQueryParams, Query()],
    current_user: User = Depends(_require_reviewer),
    db: Session = Depends(get_db),
) -> ChangeRecordListResponse:
    result = service.list_change_records(
        db,
        review_status=params.review_status,
        page=params.page,
        page_size=params.page_size,
    )
    return ChangeRecordListResponse(
        results=[_change_record_response(entry) for entry in result.entries],
        pagination=PaginationMeta(
            page=params.page, page_size=params.page_size, total_count=result.total_count
        ),
    )


@router.post(
    "/change-records/{change_record_id}/approve",
    response_model=ChangeRecordResponse,
    dependencies=[Depends(verify_csrf), Depends(enforce_admin_rate_limit)],
)
def approve_change_record(
    change_record_id: uuid.UUID,
    current_user: User = Depends(_require_reviewer),
    db: Session = Depends(get_db),
) -> ChangeRecordResponse:
    try:
        entry = service.approve_change_record(
            db, change_record_id=change_record_id, reviewed_by=current_user.id
        )
    except service.ChangeRecordNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Change record not found.") from exc
    except service.InvalidChangeRecordTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.flush()
    return _change_record_response(entry)


@router.post(
    "/change-records/{change_record_id}/reject",
    response_model=ChangeRecordResponse,
    dependencies=[Depends(verify_csrf), Depends(enforce_admin_rate_limit)],
)
def reject_change_record(
    change_record_id: uuid.UUID,
    current_user: User = Depends(_require_reviewer),
    db: Session = Depends(get_db),
) -> ChangeRecordResponse:
    try:
        entry = service.reject_change_record(
            db, change_record_id=change_record_id, reviewed_by=current_user.id
        )
    except service.ChangeRecordNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Change record not found.") from exc
    except service.InvalidChangeRecordTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.flush()
    return _change_record_response(entry)


@router.get("/verification/queue", response_model=VerificationQueueResponse)
def get_verification_queue(
    params: Annotated[VerificationQueueQueryParams, Query()],
    current_user: User = Depends(_require_reviewer),
    db: Session = Depends(get_db),
) -> VerificationQueueResponse:
    result = service.get_verification_queue(
        db, entity_type=params.entity_type, page=params.page, page_size=params.page_size
    )
    return VerificationQueueResponse(
        results=[
            VerificationQueueItem(
                entity_type=entry.entity_type,
                entity_id=entry.entity_id,
                title=entry.title,
                route=entry.route,
                verification_status=entry.verification_status,
                last_verified=entry.last_verified,
                source_organization=entry.source_organization,
            )
            for entry in result.entries
        ],
        pagination=PaginationMeta(
            page=params.page, page_size=params.page_size, total_count=result.total_count
        ),
    )


@router.post(
    "/verification/{entity_type}/{entity_id}",
    response_model=VerificationRecordResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf), Depends(enforce_admin_rate_limit)],
)
def submit_verification(
    entity_type: AdminEntityType,
    entity_id: uuid.UUID,
    payload: SubmitVerificationRequest,
    current_user: User = Depends(_require_reviewer),
    db: Session = Depends(get_db),
) -> VerificationRecordResponse:
    try:
        record = service.submit_verification(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            status=payload.status,
            source_id=payload.source_id,
            verified_by=current_user.id,
            review_due_at=payload.review_due_at,
        )
    except service.EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entity not found.") from exc
    except service.SourceNotFoundError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    db.flush()
    return VerificationRecordResponse(
        id=record.id,
        entity_type=record.entity_type,
        entity_id=record.entity_id,
        source_id=record.source_id,
        status=record.status,
        verified_by=record.verified_by,
        verified_at=record.verified_at,
        review_due_at=record.review_due_at,
    )


@router.get("/sources", response_model=SourceListResponse)
def list_sources(
    params: Annotated[PageQueryParams, Query()],
    current_user: User = Depends(_require_reviewer),
    db: Session = Depends(get_db),
) -> SourceListResponse:
    result = service.list_sources(db, page=params.page, page_size=params.page_size)
    return SourceListResponse(
        results=[
            SourceSummary(
                id=row.source.id,
                url=row.source.url,
                title=row.source.title,
                organization=row.source.organization,
                source_type=row.source.source_type,
                published_date=row.source.published_date,
                retrieved_date=row.source.retrieved_date,
                version_count=row.version_count,
            )
            for row in result.rows
        ],
        pagination=PaginationMeta(
            page=params.page, page_size=params.page_size, total_count=result.total_count
        ),
    )


@router.get("/sources/{source_id}", response_model=SourceDetailResponse)
def get_source_detail(
    source_id: uuid.UUID,
    current_user: User = Depends(_require_reviewer),
    db: Session = Depends(get_db),
) -> SourceDetailResponse:
    source = service.get_source_detail(db, source_id=source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")
    return SourceDetailResponse(
        id=source.id,
        url=source.url,
        title=source.title,
        organization=source.organization,
        source_type=source.source_type,
        published_date=source.published_date,
        retrieved_date=source.retrieved_date,
        versions=[
            SourceVersionSummary(
                id=v.id,
                content_hash=v.content_hash,
                snapshot_ref=v.snapshot_ref,
                captured_at=v.captured_at,
            )
            for v in source.versions
        ],
    )
