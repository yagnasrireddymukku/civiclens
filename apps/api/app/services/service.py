"""Service domain query/business logic — the only code path that reads
`services`/`service_requirements`/`service_required_documents`/
`service_application_methods` for the public API, and the only place
that keeps a service's Civic Search projection in sync with its
publication/verification state (docs/SEARCH.md §15, this phase's §13).

Mirrors `app.jobs.service` exactly — same visibility rule, same
search-sync shape, same query pattern — since Services is the second
real domain module following the pattern Jobs (Phase 6) established.

Visibility rule, applied identically everywhere a service is read (list,
detail, and the search-index sync below): a service is publicly visible
only when `publication_status == PUBLISHED`, `verification_status` is
`VERIFIED`/`NEEDS_REVIEW` (never `UNVERIFIED`/`EXPIRED`), and it has not
been soft-deleted — this phase's §12 ("reuse the CivicLens trust
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
from app.requirements.enums import DeliveryMode
from app.search import service as search_service
from app.services.enums import ServiceCategory, ServicePublicationStatus
from app.services.models import Service
from app.sources.enums import VerificationStatus
from app.sources.models import Source

SEARCH_ENTITY_TYPE = "service"

# Matches `app.jobs.service._PUBLIC_VERIFICATION_STATUSES` and
# `app.search.service._INDEXABLE_STATUSES` exactly, not by accident: all
# three enforce docs/DATA_GOVERNANCE.md §4's four-state model the same
# way.
_PUBLIC_VERIFICATION_STATUSES = (VerificationStatus.VERIFIED, VerificationStatus.NEEDS_REVIEW)


def _visible_predicate() -> Any:
    return and_(
        Service.publication_status == ServicePublicationStatus.PUBLISHED,
        Service.verification_status.in_(_PUBLIC_VERIFICATION_STATUSES),
        Service.deleted_at.is_(None),
    )


def is_publicly_visible(service: Service) -> bool:
    return (
        service.publication_status == ServicePublicationStatus.PUBLISHED
        and service.verification_status in _PUBLIC_VERIFICATION_STATUSES
        and service.deleted_at is None
    )


def sync_service_search_index(session: Session, service: Service) -> None:
    """Called after a service is created or its publication/verification
    state changes. Indexes it if publicly visible, removes it from the
    index otherwise — never both, and never left stale."""
    if is_publicly_visible(service):
        search_service.upsert_search_document(
            session,
            entity_type=SEARCH_ENTITY_TYPE,
            entity_id=service.id,
            locale=service.locale,
            title=service.name,
            source_id=service.source_id,
            verification_status=service.verification_status,
            summary=service.short_description,
            searchable_text=" ".join(filter(None, [service.target_audience, service.service_type])),
            route=f"/services/{service.slug}",
            state_id=service.state_id,
            district_id=service.district_id,
            category=service.category.value,
            status=service.status,
            last_verified_at=service.last_verified_at,
        )
    else:
        search_service.remove_search_document(
            session, entity_type=SEARCH_ENTITY_TYPE, entity_id=service.id, locale=service.locale
        )


@dataclass
class ServiceRow:
    service: Service
    organization: Organization
    department: Department | None
    state_name: str | None
    district_name: str | None
    source: Source


@dataclass
class ServiceListResult:
    rows: list[ServiceRow]
    total_count: int


def _base_service_select() -> Select[Any]:
    return (
        select(Service, Organization, Department, State.name, District.name, Source)
        .join(Organization, Service.organization_id == Organization.id)
        .outerjoin(Department, Service.department_id == Department.id)
        # Outer joins (unlike Job's required state_id): a service may be
        # available statewide/nationally rather than scoped to one state.
        .outerjoin(State, Service.state_id == State.id)
        .outerjoin(District, Service.district_id == District.id)
        .join(Source, Service.source_id == Source.id)
        .where(_visible_predicate())
    )


def _apply_filters(
    stmt: Select[Any],
    *,
    state_id: uuid.UUID | None,
    district_id: uuid.UUID | None,
    organization_id: uuid.UUID | None,
    department_id: uuid.UUID | None,
    category: ServiceCategory | None,
    delivery_mode: DeliveryMode | None,
    status: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select[Any]:
    if state_id is not None:
        stmt = stmt.where(Service.state_id == state_id)
    if district_id is not None:
        stmt = stmt.where(Service.district_id == district_id)
    if organization_id is not None:
        stmt = stmt.where(Service.organization_id == organization_id)
    if department_id is not None:
        stmt = stmt.where(Service.department_id == department_id)
    if category is not None:
        stmt = stmt.where(Service.category == category)
    if delivery_mode is not None:
        stmt = stmt.where(Service.delivery_mode == delivery_mode)
    if status is not None:
        stmt = stmt.where(Service.status == status)
    if date_from is not None:
        stmt = stmt.where(Service.last_verified_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Service.last_verified_at <= date_to)
    return stmt


def list_services(
    session: Session,
    *,
    state_id: uuid.UUID | None = None,
    district_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    category: ServiceCategory | None = None,
    delivery_mode: DeliveryMode | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ServiceListResult:
    """`sort` isn't a parameter here — see `app.jobs.service.list_jobs`'s
    identical docstring note: "recent" is the only sort this phase
    implements (this phase's §13 prohibits popularity ranking), so
    there's nothing to branch on yet."""
    filter_kwargs: dict[str, Any] = dict(
        state_id=state_id,
        district_id=district_id,
        organization_id=organization_id,
        department_id=department_id,
        category=category,
        delivery_mode=delivery_mode,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    count_stmt = _apply_filters(
        select(func.count()).select_from(Service).where(_visible_predicate()), **filter_kwargs
    )
    total_count = session.scalar(count_stmt) or 0

    row_stmt = _apply_filters(_base_service_select(), **filter_kwargs)
    row_stmt = row_stmt.order_by(Service.last_verified_at.desc().nullslast())
    row_stmt = row_stmt.offset((page - 1) * page_size).limit(page_size)

    rows = [
        ServiceRow(
            service=service,
            organization=organization,
            department=department,
            state_name=state_name,
            district_name=district_name,
            source=source,
        )
        for service, organization, department, state_name, district_name, source in session.execute(
            row_stmt
        ).all()
    ]
    return ServiceListResult(rows=rows, total_count=total_count)


def get_service_by_slug(session: Session, slug: str) -> ServiceRow | None:
    """Returns `None` for a service that doesn't exist *or* isn't
    publicly visible — the route layer maps both to an identical 404,
    matching `app.jobs.service.get_job_by_slug`'s identical contract."""
    stmt = (
        _base_service_select()
        .where(Service.slug == slug)
        .options(
            selectinload(Service.requirements),
            selectinload(Service.required_documents),
            selectinload(Service.application_methods),
        )
    )
    result = session.execute(stmt).first()
    if result is None:
        return None
    service, organization, department, state_name, district_name, source = result
    return ServiceRow(
        service=service,
        organization=organization,
        department=department,
        state_name=state_name,
        district_name=district_name,
        source=source,
    )
