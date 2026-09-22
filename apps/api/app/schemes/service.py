"""Scheme domain query/business logic — the only code path that reads
`schemes`/`scheme_benefits`/`scheme_requirements`/
`scheme_required_documents`/`scheme_application_methods`/
`scheme_related_services` for the public API, and the only place that
keeps a scheme's Civic Search projection in sync with its
publication/verification state (docs/SEARCH.md §16, this phase's §13).

Mirrors `app.services.service` exactly — same visibility rule, same
search-sync shape, same query pattern — since Schemes is the third real
domain module following the pattern Jobs (Phase 6) and Services
(Phase 7) established.

Visibility rule, applied identically everywhere a scheme is read (list,
detail, and the search-index sync below): a scheme is publicly visible
only when `publication_status == PUBLISHED`, `verification_status` is
`VERIFIED`/`NEEDS_REVIEW` (never `UNVERIFIED`/`EXPIRED`), and it has not
been soft-deleted — this phase's §15 ("reuse the CivicLens trust
boundary established in Phase 6").
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.geography.models import District, State
from app.institutions.models import Department, Organization
from app.schemes.enums import EducationLevel, SchemeCategory, SchemePublicationStatus
from app.schemes.models import Scheme, SchemeRelatedService, ScholarshipDetail
from app.search import service as search_service
from app.sources.enums import VerificationStatus
from app.sources.models import Source

SEARCH_ENTITY_TYPE = "scheme"

# Matches `app.jobs.service._PUBLIC_VERIFICATION_STATUSES` and
# `app.services.service._PUBLIC_VERIFICATION_STATUSES` exactly, not by
# accident: all three enforce docs/DATA_GOVERNANCE.md §4's four-state
# model the same way.
_PUBLIC_VERIFICATION_STATUSES = (VerificationStatus.VERIFIED, VerificationStatus.NEEDS_REVIEW)


def _visible_predicate() -> Any:
    return and_(
        Scheme.publication_status == SchemePublicationStatus.PUBLISHED,
        Scheme.verification_status.in_(_PUBLIC_VERIFICATION_STATUSES),
        Scheme.deleted_at.is_(None),
    )


def is_publicly_visible(scheme: Scheme) -> bool:
    return (
        scheme.publication_status == SchemePublicationStatus.PUBLISHED
        and scheme.verification_status in _PUBLIC_VERIFICATION_STATUSES
        and scheme.deleted_at is None
    )


def sync_scheme_search_index(session: Session, scheme: Scheme) -> None:
    """Called after a scheme is created or its publication/verification
    state changes. Indexes it if publicly visible, removes it from the
    index otherwise — never both, and never left stale."""
    if is_publicly_visible(scheme):
        search_service.upsert_search_document(
            session,
            entity_type=SEARCH_ENTITY_TYPE,
            entity_id=scheme.id,
            locale=scheme.locale,
            title=scheme.name,
            source_id=scheme.source_id,
            verification_status=scheme.verification_status,
            summary=scheme.short_description,
            searchable_text=scheme.target_audience,
            route=f"/schemes/{scheme.slug}",
            state_id=scheme.state_id,
            district_id=scheme.district_id,
            category=scheme.category.value,
            status=scheme.status,
            last_verified_at=scheme.last_verified_at,
        )
    else:
        search_service.remove_search_document(
            session, entity_type=SEARCH_ENTITY_TYPE, entity_id=scheme.id, locale=scheme.locale
        )


@dataclass
class SchemeRow:
    scheme: Scheme
    organization: Organization
    department: Department | None
    state_name: str | None
    district_name: str | None
    source: Source


@dataclass
class SchemeListResult:
    rows: list[SchemeRow]
    total_count: int


def _base_scheme_select() -> Select[Any]:
    return (
        select(Scheme, Organization, Department, State.name, District.name, Source)
        .join(Organization, Scheme.organization_id == Organization.id)
        .outerjoin(Department, Scheme.department_id == Department.id)
        # Outer joins (unlike Job's required state_id): a scheme may be
        # available statewide/nationally rather than scoped to one state.
        .outerjoin(State, Scheme.state_id == State.id)
        .outerjoin(District, Scheme.district_id == District.id)
        .join(Source, Scheme.source_id == Source.id)
        .where(_visible_predicate())
    )


def _apply_filters(
    stmt: Select[Any],
    *,
    state_id: uuid.UUID | None,
    district_id: uuid.UUID | None,
    organization_id: uuid.UUID | None,
    department_id: uuid.UUID | None,
    category: SchemeCategory | None,
    education_level: EducationLevel | None,
    status: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select[Any]:
    if state_id is not None:
        stmt = stmt.where(Scheme.state_id == state_id)
    if district_id is not None:
        stmt = stmt.where(Scheme.district_id == district_id)
    if organization_id is not None:
        stmt = stmt.where(Scheme.organization_id == organization_id)
    if department_id is not None:
        stmt = stmt.where(Scheme.department_id == department_id)
    if category is not None:
        stmt = stmt.where(Scheme.category == category)
    if education_level is not None:
        # Only joined when this (rarely-used, scholarship-specific)
        # filter is actually supplied — every other filter above applies
        # to every scheme, so an unconditional join here would cost
        # every list/count query for a filter most callers never pass.
        stmt = stmt.join(ScholarshipDetail, Scheme.id == ScholarshipDetail.scheme_id).where(
            ScholarshipDetail.education_level == education_level
        )
    if status is not None:
        stmt = stmt.where(Scheme.status == status)
    if date_from is not None:
        stmt = stmt.where(Scheme.last_verified_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Scheme.last_verified_at <= date_to)
    return stmt


def list_schemes(
    session: Session,
    *,
    state_id: uuid.UUID | None = None,
    district_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    category: SchemeCategory | None = None,
    education_level: EducationLevel | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SchemeListResult:
    """`sort` isn't a parameter here — see `app.services.service.list_services`'s
    identical docstring note: "recent" is the only sort this phase
    implements (this phase's §15 prohibits popularity ranking), so
    there's nothing to branch on yet."""
    filter_kwargs: dict[str, Any] = dict(
        state_id=state_id,
        district_id=district_id,
        organization_id=organization_id,
        department_id=department_id,
        category=category,
        education_level=education_level,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    count_stmt = _apply_filters(
        select(func.count()).select_from(Scheme).where(_visible_predicate()), **filter_kwargs
    )
    total_count = session.scalar(count_stmt) or 0

    row_stmt = _apply_filters(_base_scheme_select(), **filter_kwargs)
    row_stmt = row_stmt.order_by(Scheme.last_verified_at.desc().nullslast())
    row_stmt = row_stmt.offset((page - 1) * page_size).limit(page_size)

    rows = [
        SchemeRow(
            scheme=scheme,
            organization=organization,
            department=department,
            state_name=state_name,
            district_name=district_name,
            source=source,
        )
        for scheme, organization, department, state_name, district_name, source in session.execute(
            row_stmt
        ).all()
    ]
    return SchemeListResult(rows=rows, total_count=total_count)


def get_scheme_by_slug(session: Session, slug: str) -> SchemeRow | None:
    """Returns `None` for a scheme that doesn't exist *or* isn't
    publicly visible — the route layer maps both to an identical 404,
    matching `app.services.service.get_service_by_slug`'s identical
    contract."""
    stmt = (
        _base_scheme_select()
        .where(Scheme.slug == slug)
        .options(
            selectinload(Scheme.benefits),
            selectinload(Scheme.requirements),
            selectinload(Scheme.required_documents),
            selectinload(Scheme.application_methods),
            selectinload(Scheme.related_services).selectinload(SchemeRelatedService.service),
            selectinload(Scheme.scholarship_detail),
        )
    )
    result = session.execute(stmt).first()
    if result is None:
        return None
    scheme, organization, department, state_name, district_name, source = result
    return SchemeRow(
        scheme=scheme,
        organization=organization,
        department=department,
        state_name=state_name,
        district_name=district_name,
        source=source,
    )
