"""Tracking domain logic — the only module that writes `tracked_items`.

Entity resolution reuses each domain's own `get_*_by_slug` (already
applies that domain's visibility rule) — the same cross-module-read
pattern `app.ai.entity_resolution`/`app.eligibility.service` already
established. Display data for a listed tracked item is read from
`search_documents` (title/route/verification_status/last_verified),
not re-fetched from each domain separately — the same reuse decision
Phase 12 made for retrieval, applied a third time: an entity that drops
out of `search_documents` (unpublished/expired/deleted) is exactly the
"no longer available" signal this phase's §8 asks tracking to handle
safely, obtained for free rather than re-implemented.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents import service as documents_service
from app.jobs import service as jobs_service
from app.schemes import service as schemes_service
from app.search.models import SearchDocument
from app.services import service as services_service
from app.sources.enums import VerificationStatus
from app.sources.models import Source
from app.tracking.enums import TrackedEntityType
from app.tracking.models import TrackedItem

_FK_COLUMN_NAME = {
    TrackedEntityType.JOB: "job_id",
    TrackedEntityType.SERVICE: "service_id",
    TrackedEntityType.SCHEME: "scheme_id",
    TrackedEntityType.DOCUMENT: "document_id",
}


class TrackedItemNotFoundError(Exception):
    """Raised for "doesn't exist" *or* "exists but belongs to another
    user" — the route layer maps both to an identical 404, the same
    IDOR-safe convention every other domain's `get_*_by_slug` already
    uses for "not found or not visible."""


@dataclass(frozen=True, slots=True)
class ResolvedTrackableEntity:
    entity_type: TrackedEntityType
    entity_id: uuid.UUID
    slug: str
    name: str


def resolve_entity(
    session: Session, entity_type: TrackedEntityType, slug: str
) -> ResolvedTrackableEntity | None:
    if entity_type == TrackedEntityType.JOB:
        job_row = jobs_service.get_job_by_slug(session, slug)
        return (
            None
            if job_row is None
            else ResolvedTrackableEntity(entity_type, job_row.job.id, slug, job_row.job.title)
        )
    if entity_type == TrackedEntityType.SERVICE:
        service_row = services_service.get_service_by_slug(session, slug)
        return (
            None
            if service_row is None
            else ResolvedTrackableEntity(
                entity_type, service_row.service.id, slug, service_row.service.name
            )
        )
    if entity_type == TrackedEntityType.SCHEME:
        scheme_row = schemes_service.get_scheme_by_slug(session, slug)
        return (
            None
            if scheme_row is None
            else ResolvedTrackableEntity(
                entity_type, scheme_row.scheme.id, slug, scheme_row.scheme.name
            )
        )
    if entity_type == TrackedEntityType.DOCUMENT:
        document_row = documents_service.get_document_by_slug(session, slug)
        return (
            None
            if document_row is None
            else ResolvedTrackableEntity(
                entity_type, document_row.document.id, slug, document_row.document.name
            )
        )
    raise AssertionError(f"unreachable entity_type {entity_type}")  # pragma: no cover


def entity_type_and_id(item: TrackedItem) -> tuple[TrackedEntityType, uuid.UUID]:
    """The inverse of storing the id across four nullable columns —
    exactly one is ever non-null (the `CHECK` constraint guarantees
    it)."""

    for entity_type, column_name in _FK_COLUMN_NAME.items():
        value = getattr(item, column_name)
        if value is not None:
            return entity_type, value
    raise AssertionError("unreachable: no entity FK set on TrackedItem")  # pragma: no cover


def track_entity(
    session: Session, *, user_id: uuid.UUID, entity_type: TrackedEntityType, entity_id: uuid.UUID
) -> TrackedItem:
    """Idempotent: tracking an already-tracked (even paused) entity
    reactivates the existing row rather than raising or duplicating —
    this phase's own "adding" contract never errors on a redundant
    call."""

    column_name = _FK_COLUMN_NAME[entity_type]
    existing = (
        session.query(TrackedItem)
        .filter(TrackedItem.user_id == user_id, getattr(TrackedItem, column_name) == entity_id)
        .one_or_none()
    )
    if existing is not None:
        existing.is_active = True
        existing.paused_at = None
        return existing

    item = TrackedItem(user_id=user_id, **{column_name: entity_id})
    session.add(item)
    session.flush()
    return item


def _get_owned(session: Session, *, user_id: uuid.UUID, tracked_item_id: uuid.UUID) -> TrackedItem:
    item = session.get(TrackedItem, tracked_item_id)
    if item is None or item.user_id != user_id:
        raise TrackedItemNotFoundError(tracked_item_id)
    return item


def pause_tracked_item(
    session: Session, *, user_id: uuid.UUID, tracked_item_id: uuid.UUID
) -> TrackedItem:
    item = _get_owned(session, user_id=user_id, tracked_item_id=tracked_item_id)
    item.is_active = False
    item.paused_at = datetime.now(UTC)
    return item


def resume_tracked_item(
    session: Session, *, user_id: uuid.UUID, tracked_item_id: uuid.UUID
) -> TrackedItem:
    item = _get_owned(session, user_id=user_id, tracked_item_id=tracked_item_id)
    item.is_active = True
    item.paused_at = None
    return item


def remove_tracked_item(
    session: Session, *, user_id: uuid.UUID, tracked_item_id: uuid.UUID
) -> None:
    item = _get_owned(session, user_id=user_id, tracked_item_id=tracked_item_id)
    session.delete(item)


def update_label(
    session: Session, *, user_id: uuid.UUID, tracked_item_id: uuid.UUID, label: str | None
) -> TrackedItem:
    item = _get_owned(session, user_id=user_id, tracked_item_id=tracked_item_id)
    item.label = label
    return item


@dataclass(frozen=True, slots=True)
class TrackedItemView:
    tracked_item: TrackedItem
    entity_type: TrackedEntityType
    entity_id: uuid.UUID
    title: str | None
    route: str | None
    verification_status: VerificationStatus | None
    last_verified_at: datetime | None
    source_organization: str | None
    still_available: bool


def list_tracked_items(
    session: Session, *, user_id: uuid.UUID, locale: str = "en"
) -> list[TrackedItemView]:
    """Ordered newest-first. Display fields come from `search_documents`
    (see module docstring) — `still_available=False` when the entity is
    no longer there (unpublished/expired/deleted), never guessed from
    the `TrackedItem` row alone."""

    items = (
        session.query(TrackedItem)
        .filter(TrackedItem.user_id == user_id)
        .order_by(TrackedItem.created_at.desc())
        .all()
    )
    if not items:
        return []

    keyed = {entity_type_and_id(item): item for item in items}
    search_rows = session.execute(
        select(SearchDocument, Source)
        .join(Source, SearchDocument.source_id == Source.id)
        .where(
            SearchDocument.locale == locale,
            SearchDocument.entity_type.in_({et.value for et, _ in keyed}),
            SearchDocument.entity_id.in_({eid for _, eid in keyed}),
        )
    ).all()
    display_by_key = {
        (TrackedEntityType(doc.entity_type), doc.entity_id): (doc, source)
        for doc, source in search_rows
    }

    views = []
    for (entity_type, entity_id), item in keyed.items():
        display = display_by_key.get((entity_type, entity_id))
        if display is not None:
            document, source = display
            views.append(
                TrackedItemView(
                    tracked_item=item,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    title=document.title,
                    route=document.route,
                    verification_status=document.verification_status,
                    last_verified_at=document.last_verified_at,
                    source_organization=source.organization,
                    still_available=True,
                )
            )
        else:
            views.append(
                TrackedItemView(
                    tracked_item=item,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    title=None,
                    route=None,
                    verification_status=None,
                    last_verified_at=None,
                    source_organization=None,
                    still_available=False,
                )
            )
    views.sort(key=lambda v: v.tracked_item.created_at, reverse=True)
    return views
