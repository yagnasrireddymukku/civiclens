"""Documents & Certificates domain query/business logic — the only code
path that reads `civic_documents`/`document_requirements`/
`document_supporting_documents`/`document_application_methods` for the
public API, and the only place that keeps a document's Civic Search
projection in sync with its publication/verification state
(docs/SEARCH.md §18, this phase's §17).

Mirrors `app.schemes.service` exactly — same visibility rule, same
search-sync shape, same query pattern — since Documents is the fourth
real domain module following the pattern Jobs (Phase 6), Services
(Phase 7), and Schemes (Phase 8) established.

Visibility rule, applied identically everywhere a document is read
(list, detail, and the search-index sync below): a document is publicly
visible only when `publication_status == PUBLISHED`,
`verification_status` is `VERIFIED`/`NEEDS_REVIEW` (never
`UNVERIFIED`/`EXPIRED`), and it has not been soft-deleted — this
phase's §16 ("reuse the CivicLens trust boundary established in
Phase 6").

`get_required_by()` is the one place this module reads another
domain's tables directly (`app.services.models.RequiredDocument`,
`app.schemes.models.SchemeRequiredDocument`) — not a layering
violation but the explicit reverse-relationship feature this phase's
§14/§22 asks for: each of those tables carries its own nullable
`civic_document_id` FK (added by this phase, see
`app/documents/models.py`'s module docstring), and this function reads
it the same way `app/api/v1/schemes.py` already reads
`app.services.service.is_publicly_visible` for `related_services`
(Phase 8's identical precedent for a legitimate, explicitly-modeled
cross-domain reference).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.documents.enums import DocumentCategory, DocumentPublicationStatus, DocumentType
from app.documents.models import CivicDocument, DocumentSupportingDocument
from app.geography.models import District, State
from app.institutions.models import Department, Organization
from app.requirements.enums import DeliveryMode
from app.schemes.models import Scheme, SchemeRequiredDocument
from app.schemes.service import is_publicly_visible as is_scheme_publicly_visible
from app.search import service as search_service
from app.services.models import RequiredDocument, Service
from app.services.service import is_publicly_visible as is_service_publicly_visible
from app.sources.enums import VerificationStatus
from app.sources.models import Source

SEARCH_ENTITY_TYPE = "document"

# Matches every other domain's `_PUBLIC_VERIFICATION_STATUSES` exactly,
# not by accident: all of them enforce docs/DATA_GOVERNANCE.md §4's
# four-state model the same way.
_PUBLIC_VERIFICATION_STATUSES = (VerificationStatus.VERIFIED, VerificationStatus.NEEDS_REVIEW)


def _visible_predicate() -> Any:
    return and_(
        CivicDocument.publication_status == DocumentPublicationStatus.PUBLISHED,
        CivicDocument.verification_status.in_(_PUBLIC_VERIFICATION_STATUSES),
        CivicDocument.deleted_at.is_(None),
    )


def is_publicly_visible(document: CivicDocument) -> bool:
    return (
        document.publication_status == DocumentPublicationStatus.PUBLISHED
        and document.verification_status in _PUBLIC_VERIFICATION_STATUSES
        and document.deleted_at is None
    )


def sync_document_search_index(session: Session, document: CivicDocument) -> None:
    """Called after a document is created or its publication/
    verification state changes. Indexes it if publicly visible, removes
    it from the index otherwise — never both, and never left stale."""
    if is_publicly_visible(document):
        search_service.upsert_search_document(
            session,
            entity_type=SEARCH_ENTITY_TYPE,
            entity_id=document.id,
            locale=document.locale,
            title=document.name,
            source_id=document.source_id,
            verification_status=document.verification_status,
            summary=document.short_description,
            searchable_text=document.purpose,
            route=f"/documents/{document.slug}",
            state_id=document.state_id,
            district_id=document.district_id,
            category=document.category.value,
            status=document.status,
            last_verified_at=document.last_verified_at,
        )
    else:
        search_service.remove_search_document(
            session, entity_type=SEARCH_ENTITY_TYPE, entity_id=document.id, locale=document.locale
        )


@dataclass
class DocumentRow:
    document: CivicDocument
    organization: Organization
    department: Department | None
    state_name: str | None
    district_name: str | None
    source: Source


@dataclass
class DocumentListResult:
    rows: list[DocumentRow]
    total_count: int


def _base_document_select() -> Select[Any]:
    return (
        select(CivicDocument, Organization, Department, State.name, District.name, Source)
        .join(Organization, CivicDocument.organization_id == Organization.id)
        .outerjoin(Department, CivicDocument.department_id == Department.id)
        # Outer joins (unlike Job's required state_id): a document may be
        # issued statewide/nationally rather than scoped to one state.
        .outerjoin(State, CivicDocument.state_id == State.id)
        .outerjoin(District, CivicDocument.district_id == District.id)
        .join(Source, CivicDocument.source_id == Source.id)
        .where(_visible_predicate())
    )


def _apply_filters(
    stmt: Select[Any],
    *,
    state_id: uuid.UUID | None,
    district_id: uuid.UUID | None,
    organization_id: uuid.UUID | None,
    department_id: uuid.UUID | None,
    document_type: DocumentType | None,
    category: DocumentCategory | None,
    delivery_mode: DeliveryMode | None,
    status: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select[Any]:
    if state_id is not None:
        stmt = stmt.where(CivicDocument.state_id == state_id)
    if district_id is not None:
        stmt = stmt.where(CivicDocument.district_id == district_id)
    if organization_id is not None:
        stmt = stmt.where(CivicDocument.organization_id == organization_id)
    if department_id is not None:
        stmt = stmt.where(CivicDocument.department_id == department_id)
    if document_type is not None:
        stmt = stmt.where(CivicDocument.document_type == document_type)
    if category is not None:
        stmt = stmt.where(CivicDocument.category == category)
    if delivery_mode is not None:
        stmt = stmt.where(CivicDocument.delivery_mode == delivery_mode)
    if status is not None:
        stmt = stmt.where(CivicDocument.status == status)
    if date_from is not None:
        stmt = stmt.where(CivicDocument.last_verified_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(CivicDocument.last_verified_at <= date_to)
    return stmt


def list_documents(
    session: Session,
    *,
    state_id: uuid.UUID | None = None,
    district_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    document_type: DocumentType | None = None,
    category: DocumentCategory | None = None,
    delivery_mode: DeliveryMode | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> DocumentListResult:
    """`sort` isn't a parameter here — see `app.schemes.service.list_schemes`'s
    identical docstring note: "recent" is the only sort this phase
    implements (this phase prohibits popularity ranking), so there's
    nothing to branch on yet."""
    filter_kwargs: dict[str, Any] = dict(
        state_id=state_id,
        district_id=district_id,
        organization_id=organization_id,
        department_id=department_id,
        document_type=document_type,
        category=category,
        delivery_mode=delivery_mode,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    count_stmt = _apply_filters(
        select(func.count()).select_from(CivicDocument).where(_visible_predicate()),
        **filter_kwargs,
    )
    total_count = session.scalar(count_stmt) or 0

    row_stmt = _apply_filters(_base_document_select(), **filter_kwargs)
    row_stmt = row_stmt.order_by(CivicDocument.last_verified_at.desc().nullslast())
    row_stmt = row_stmt.offset((page - 1) * page_size).limit(page_size)

    rows = [
        DocumentRow(
            document=document,
            organization=organization,
            department=department,
            state_name=state_name,
            district_name=district_name,
            source=source,
        )
        for document, organization, department, state_name, district_name, source in (
            session.execute(row_stmt).all()
        )
    ]
    return DocumentListResult(rows=rows, total_count=total_count)


def get_document_by_slug(session: Session, slug: str) -> DocumentRow | None:
    """Returns `None` for a document that doesn't exist *or* isn't
    publicly visible — the route layer maps both to an identical 404,
    matching every other domain's identical contract."""
    stmt = (
        _base_document_select()
        .where(CivicDocument.slug == slug)
        .options(
            selectinload(CivicDocument.requirements),
            selectinload(CivicDocument.supporting_documents).selectinload(
                DocumentSupportingDocument.civic_document
            ),
            selectinload(CivicDocument.application_methods),
            selectinload(CivicDocument.service),
        )
    )
    result = session.execute(stmt).first()
    if result is None:
        return None
    document, organization, department, state_name, district_name, source = result
    return DocumentRow(
        document=document,
        organization=organization,
        department=department,
        state_name=state_name,
        district_name=district_name,
        source=source,
    )


@dataclass
class RequiredByRow:
    entity_type: Literal["service", "scheme"]
    slug: str
    name: str


def get_required_by(session: Session, document_id: uuid.UUID) -> list[RequiredByRow]:
    """ "Where this document may be required" (this phase's §14/§22) —
    only ever built from an explicit `civic_document_id` link on
    `RequiredDocument`/`SchemeRequiredDocument`, never inferred from
    matching names. Covers Scholarships transparently: a scholarship is
    a `Scheme` (Phase 9), so a scholarship's required documents already
    live in `scheme_required_documents`. Jobs have no document-
    requirement structure yet (verified by hand — `app.jobs.models` has
    no such table), so they never appear here; that is an accurate
    absence, not a gap in this query.
    """
    rows: list[RequiredByRow] = []

    service_stmt = (
        select(Service, RequiredDocument)
        .join(RequiredDocument, RequiredDocument.service_id == Service.id)
        .where(RequiredDocument.civic_document_id == document_id)
    )
    for service, _required_document in session.execute(service_stmt).all():
        if is_service_publicly_visible(service):
            rows.append(RequiredByRow(entity_type="service", slug=service.slug, name=service.name))

    scheme_stmt = (
        select(Scheme, SchemeRequiredDocument)
        .join(SchemeRequiredDocument, SchemeRequiredDocument.scheme_id == Scheme.id)
        .where(SchemeRequiredDocument.civic_document_id == document_id)
    )
    for scheme, _scheme_required_document in session.execute(scheme_stmt).all():
        if is_scheme_publicly_visible(scheme):
            rows.append(RequiredByRow(entity_type="scheme", slug=scheme.slug, name=scheme.name))

    return rows
