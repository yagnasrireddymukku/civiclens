"""Admin Intelligence Center orchestration — the review/approval
console for already-detected `ChangeRecord`s and entity verification
decisions.

**Scope note, since this diverges from docs/ROADMAP.md's original
Phase 13 sketch — documented here rather than silently redefined.**
`services/ingestion/`, live source fetching, and per-source
legal-checklist onboarding tooling (docs/DATA_SOURCES.md §2-3) remain
entirely unbuilt: this module never fetches anything from a real
source, and no autonomous or scraping-driven data entry exists
anywhere in this codebase. Every `ChangeRecord` this module can review
was produced by `app.tracking.change_detection.detect_changes`
(Tracking + Notifications, rescheduled from Phase 12), which compares
an entity's *already-current* database value against its own prior
recorded value — there is no staging table an approval "publishes"
from (the target staging-table architecture in
docs/DATA_SOURCES.md §3 remains a future build). Approving a
`ChangeRecord` here therefore means "a human reviewer confirms this
already-live change is legitimate and trackers should be notified
about it," not "this change becomes live" — it already is, by
construction of how `detect_changes` works. Approving a
`VerificationRecord` is the action in this module with a directly
public effect: it is the only place in this codebase that writes to a
fact-bearing entity's own `verification_status` column (previously
only ever set by fixtures/tests), which gates search/AI/tracking
visibility per every domain's own established `is_publicly_visible`
rule.

**Source management is read-only this phase.** No route here creates a
`Source` or a `SourceVersion` — doing so would mean either fabricating
verification evidence (a `SourceVersion.content_hash` with no real
fetched content behind it) or reimplementing a slice of the
still-unbuilt ingestion pipeline. This phase's admin console only
browses existing `Source`/`SourceVersion` rows (currently written by
domain fixtures), consistent with the explicit "avoid accepting
fabricated verification evidence" requirement.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin.enums import AdminEntityType
from app.documents.models import CivicDocument
from app.documents.service import sync_document_search_index
from app.jobs.models import Job
from app.jobs.service import sync_job_search_index
from app.notifications.generation import generate_change_notifications
from app.schemes.models import Scheme
from app.schemes.service import sync_scheme_search_index
from app.services.models import Service
from app.services.service import sync_service_search_index
from app.sources.enums import ChangeReviewStatus, VerificationStatus
from app.sources.models import ChangeRecord, Source, SourceVersion, VerificationRecord
from app.tracking.change_detection import approve_change_record as _mark_change_approved
from app.tracking.change_detection import reject_change_record as _mark_change_rejected

EntityModel = Job | Scheme | Service | CivicDocument


class ChangeRecordNotFoundError(Exception):
    """No such change record."""


class InvalidChangeRecordTransitionError(Exception):
    """The record was already decided the other way — approving an
    already-rejected record or rejecting an already-approved one is
    refused, never silently overwritten (this phase's explicit
    "enforce valid state transitions"). Approving/rejecting a record
    that already holds *that same* decision is a no-op, not an error —
    the idempotent-retry case."""


class EntityNotFoundError(Exception):
    """No such job/service/scheme/document."""


class SourceNotFoundError(Exception):
    """The evidence `source_id` does not reference a real `Source` row
    — "never accept fabricated verification evidence" (this phase's
    explicit requirement)."""


_ROUTE_PREFIX: dict[AdminEntityType, str] = {
    AdminEntityType.JOB: "jobs",
    AdminEntityType.SCHEME: "schemes",
    AdminEntityType.SERVICE: "services",
    AdminEntityType.DOCUMENT: "documents",
}

# Entity types with an all-4-domains query (the verification queue,
# `get_dashboard_metrics`'s status counts) iterate this rather than a
# dict of model *types* — `session.get(some_var_holding_a_type, id)`
# and `select(some_var_holding_a_type)` both lose their specific
# return/attribute type when the type itself came out of a dict keyed
# by a Union (mypy falls back to the ORM `Base` class and every
# attribute access then errors "Base has no attribute ..."). Every
# function below that needs a concrete, attribute-accessible model
# therefore dispatches with explicit if/elif on `AdminEntityType`
# instead, the same fix already established for `_sync_search_index`
# below (and, before this phase, `app.ai.chunking._BUILDERS`).
ALL_ENTITY_TYPES: tuple[AdminEntityType, ...] = tuple(AdminEntityType)


def _get_entity(
    session: Session, entity_type: AdminEntityType, entity_id: uuid.UUID
) -> EntityModel | None:
    if entity_type == AdminEntityType.JOB:
        return session.get(Job, entity_id)
    elif entity_type == AdminEntityType.SCHEME:
        return session.get(Scheme, entity_id)
    elif entity_type == AdminEntityType.SERVICE:
        return session.get(Service, entity_id)
    elif entity_type == AdminEntityType.DOCUMENT:
        return session.get(CivicDocument, entity_id)
    else:  # pragma: no cover - AdminEntityType is exhaustively handled above
        raise AssertionError(f"unreachable entity_type {entity_type}")


def _list_entities_needing_review(
    session: Session, entity_type: AdminEntityType, statuses: tuple[VerificationStatus, ...]
) -> list[EntityModel]:
    if entity_type == AdminEntityType.JOB:
        return list(
            session.execute(select(Job).where(Job.verification_status.in_(statuses))).scalars()
        )
    elif entity_type == AdminEntityType.SCHEME:
        return list(
            session.execute(
                select(Scheme).where(Scheme.verification_status.in_(statuses))
            ).scalars()
        )
    elif entity_type == AdminEntityType.SERVICE:
        return list(
            session.execute(
                select(Service).where(Service.verification_status.in_(statuses))
            ).scalars()
        )
    elif entity_type == AdminEntityType.DOCUMENT:
        return list(
            session.execute(
                select(CivicDocument).where(CivicDocument.verification_status.in_(statuses))
            ).scalars()
        )
    else:  # pragma: no cover - AdminEntityType is exhaustively handled above
        raise AssertionError(f"unreachable entity_type {entity_type}")


def _verification_status_counts_for(
    session: Session, entity_type: AdminEntityType
) -> list[tuple[VerificationStatus, int]]:
    if entity_type == AdminEntityType.JOB:
        stmt = select(Job.verification_status, func.count()).group_by(Job.verification_status)
    elif entity_type == AdminEntityType.SCHEME:
        stmt = select(Scheme.verification_status, func.count()).group_by(Scheme.verification_status)
    elif entity_type == AdminEntityType.SERVICE:
        stmt = select(Service.verification_status, func.count()).group_by(
            Service.verification_status
        )
    elif entity_type == AdminEntityType.DOCUMENT:
        stmt = select(CivicDocument.verification_status, func.count()).group_by(
            CivicDocument.verification_status
        )
    else:  # pragma: no cover - AdminEntityType is exhaustively handled above
        raise AssertionError(f"unreachable entity_type {entity_type}")
    return [(status, count) for status, count in session.execute(stmt).all()]


def _entity_title(entity: EntityModel) -> str:
    return entity.title if isinstance(entity, Job) else entity.name


def _entity_route(entity_type: AdminEntityType, slug: str) -> str:
    return f"/{_ROUTE_PREFIX[entity_type]}/{slug}"


def _sync_search_index(entity_type: AdminEntityType, session: Session, entity: EntityModel) -> None:
    # Explicit dispatch, not a dict of callables: a dict keyed by
    # entity type whose values are functions with different parameter
    # types each is exactly the `app.ai.chunking._BUILDERS` pattern
    # this codebase already hit and reverted (mypy "Cannot call
    # function of unknown type") — if/elif avoids it, matching that
    # established fix.
    if entity_type == AdminEntityType.JOB and isinstance(entity, Job):
        sync_job_search_index(session, entity)
    elif entity_type == AdminEntityType.SCHEME and isinstance(entity, Scheme):
        sync_scheme_search_index(session, entity)
    elif entity_type == AdminEntityType.SERVICE and isinstance(entity, Service):
        sync_service_search_index(session, entity)
    elif entity_type == AdminEntityType.DOCUMENT and isinstance(entity, CivicDocument):
        sync_document_search_index(session, entity)
    else:  # pragma: no cover - AdminEntityType is exhaustively handled above
        raise AssertionError(f"unreachable entity_type {entity_type}")


@dataclass(frozen=True, slots=True)
class EntityDisplay:
    title: str | None
    route: str | None
    verification_status: VerificationStatus | None
    source_organization: str | None


_MISSING_DISPLAY = EntityDisplay(
    title=None, route=None, verification_status=None, source_organization=None
)


def _get_entity_display(
    session: Session, entity_type_raw: str, entity_id: uuid.UUID
) -> EntityDisplay:
    """Never raises — a `ChangeRecord` may reference an entity type
    this admin console doesn't (yet) recognize, or an entity since
    deleted; both render as "no longer available" display data rather
    than a broken review queue."""
    try:
        entity_type = AdminEntityType(entity_type_raw)
    except ValueError:
        return _MISSING_DISPLAY

    entity = _get_entity(session, entity_type, entity_id)
    if entity is None:
        return _MISSING_DISPLAY

    source = session.get(Source, entity.source_id)
    return EntityDisplay(
        title=_entity_title(entity),
        route=_entity_route(entity_type, entity.slug),
        verification_status=entity.verification_status,
        source_organization=source.organization if source is not None else None,
    )


# ---------------------------------------------------------------------------
# Change-record review queue
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChangeRecordEntry:
    record: ChangeRecord
    display: EntityDisplay


@dataclass(frozen=True, slots=True)
class ChangeRecordListResult:
    entries: list[ChangeRecordEntry]
    total_count: int


def list_change_records(
    session: Session,
    *,
    review_status: ChangeReviewStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ChangeRecordListResult:
    count_stmt = select(func.count()).select_from(ChangeRecord)
    row_stmt = select(ChangeRecord)
    if review_status is not None:
        count_stmt = count_stmt.where(ChangeRecord.review_status == review_status)
        row_stmt = row_stmt.where(ChangeRecord.review_status == review_status)

    total_count = session.scalar(count_stmt) or 0
    row_stmt = (
        row_stmt.order_by(ChangeRecord.detected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    records = session.execute(row_stmt).scalars().all()
    entries = [
        ChangeRecordEntry(
            record=record,
            display=_get_entity_display(session, record.entity_type, record.entity_id),
        )
        for record in records
    ]
    return ChangeRecordListResult(entries=entries, total_count=total_count)


def approve_change_record(
    session: Session, *, change_record_id: uuid.UUID, reviewed_by: uuid.UUID
) -> ChangeRecordEntry:
    record = session.get(ChangeRecord, change_record_id)
    if record is None:
        raise ChangeRecordNotFoundError(change_record_id)
    if record.review_status == ChangeReviewStatus.REJECTED:
        raise InvalidChangeRecordTransitionError(
            f"Change record {change_record_id} was already rejected and cannot be approved."
        )
    if record.review_status == ChangeReviewStatus.PENDING:
        _mark_change_approved(session, change_record_id=change_record_id, reviewed_by=reviewed_by)
        session.flush()

    # Idempotent and dedup-safe either way (create_notification's
    # database-level ON CONFLICT DO NOTHING) — re-running this after a
    # retried request, or after a crash between the line above and
    # here, never produces a duplicate notification.
    generate_change_notifications(session)
    session.flush()
    return ChangeRecordEntry(
        record=record, display=_get_entity_display(session, record.entity_type, record.entity_id)
    )


def reject_change_record(
    session: Session, *, change_record_id: uuid.UUID, reviewed_by: uuid.UUID
) -> ChangeRecordEntry:
    record = session.get(ChangeRecord, change_record_id)
    if record is None:
        raise ChangeRecordNotFoundError(change_record_id)
    if record.review_status == ChangeReviewStatus.APPROVED:
        raise InvalidChangeRecordTransitionError(
            f"Change record {change_record_id} was already approved and cannot be rejected."
        )
    if record.review_status == ChangeReviewStatus.PENDING:
        _mark_change_rejected(session, change_record_id=change_record_id, reviewed_by=reviewed_by)
        session.flush()
    return ChangeRecordEntry(
        record=record, display=_get_entity_display(session, record.entity_type, record.entity_id)
    )


# ---------------------------------------------------------------------------
# Verification queue
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VerificationQueueEntry:
    entity_type: AdminEntityType
    entity_id: uuid.UUID
    title: str
    route: str
    verification_status: VerificationStatus
    last_verified: datetime | None
    source_organization: str | None


@dataclass(frozen=True, slots=True)
class VerificationQueueResult:
    entries: list[VerificationQueueEntry]
    total_count: int


DEFAULT_QUEUE_STATUSES: tuple[VerificationStatus, ...] = (
    VerificationStatus.NEEDS_REVIEW,
    VerificationStatus.UNVERIFIED,
)


def get_verification_queue(
    session: Session,
    *,
    entity_type: AdminEntityType | None = None,
    statuses: tuple[VerificationStatus, ...] = DEFAULT_QUEUE_STATUSES,
    page: int = 1,
    page_size: int = 20,
) -> VerificationQueueResult:
    """Deliberately not one SQL query: the four entity tables have no
    common base table to `UNION` across, so each is queried in full
    (filtered) and the combined queue is sorted/paginated in Python.
    Acceptable at this project's actual fixture-only scale
    (CLAUDE.md rule 12, avoid premature optimization) — a real-data
    volume would need a materialized queue table instead."""
    entity_types = [entity_type] if entity_type is not None else list(ALL_ENTITY_TYPES)

    entries: list[VerificationQueueEntry] = []
    for et in entity_types:
        for entity in _list_entities_needing_review(session, et, statuses):
            source = session.get(Source, entity.source_id)
            entries.append(
                VerificationQueueEntry(
                    entity_type=et,
                    entity_id=entity.id,
                    title=_entity_title(entity),
                    route=_entity_route(et, entity.slug),
                    verification_status=entity.verification_status,
                    last_verified=entity.last_verified_at,
                    source_organization=source.organization if source is not None else None,
                )
            )

    total_count = len(entries)
    entries.sort(key=lambda e: e.last_verified or datetime.min.replace(tzinfo=UTC))
    start = (page - 1) * page_size
    page_entries = entries[start : start + page_size]
    return VerificationQueueResult(entries=page_entries, total_count=total_count)


def submit_verification(
    session: Session,
    *,
    entity_type: AdminEntityType,
    entity_id: uuid.UUID,
    status: VerificationStatus,
    source_id: uuid.UUID,
    verified_by: uuid.UUID,
    review_due_at: datetime | None = None,
) -> VerificationRecord:
    """Creates the evidence record (`VerificationRecord`, this phase's
    "record ... supporting evidence") and updates the entity's own
    `verification_status` to match in the same transaction — the two
    are never allowed to drift apart. `source_id` is required (not
    optional) at the database column level already
    (`VerificationRecord.source_id` is `nullable=False`); this function
    additionally checks the source actually exists, rather than
    letting a bad id fail as an opaque FK-violation 500 ("no approval
    without evidence" — evidence that doesn't resolve to a real row is
    treated the same as no evidence)."""
    entity = _get_entity(session, entity_type, entity_id)
    if entity is None:
        raise EntityNotFoundError(f"No such {entity_type.value}: {entity_id}")

    source = session.get(Source, source_id)
    if source is None:
        raise SourceNotFoundError(f"No such source: {source_id}")

    now = datetime.now(UTC)
    record = VerificationRecord(
        entity_type=entity_type.value,
        entity_id=entity_id,
        source_id=source_id,
        status=status,
        verified_by=verified_by,
        verified_at=now,
        review_due_at=review_due_at,
    )
    session.add(record)

    entity.verification_status = status
    entity.last_verified_at = now
    session.flush()

    _sync_search_index(entity_type, session, entity)

    return record


# ---------------------------------------------------------------------------
# Sources (read-only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceRow:
    source: Source
    version_count: int


@dataclass(frozen=True, slots=True)
class SourceListResult:
    rows: list[SourceRow]
    total_count: int


def list_sources(session: Session, *, page: int = 1, page_size: int = 20) -> SourceListResult:
    total_count = session.scalar(select(func.count()).select_from(Source)) or 0
    stmt = (
        select(Source, func.count(SourceVersion.id))
        .outerjoin(SourceVersion, SourceVersion.source_id == Source.id)
        .group_by(Source.id)
        .order_by(Source.retrieved_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = [SourceRow(source=s, version_count=c) for s, c in session.execute(stmt).all()]
    return SourceListResult(rows=rows, total_count=total_count)


def get_source_detail(session: Session, *, source_id: uuid.UUID) -> Source | None:
    return session.get(Source, source_id)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DashboardMetrics:
    pending_change_records: int
    verification_status_counts: dict[VerificationStatus, int]
    recent_change_decisions: list[ChangeRecord]
    recent_verifications: list[VerificationRecord]


def get_dashboard_metrics(session: Session, *, recent_limit: int = 10) -> DashboardMetrics:
    pending_count = (
        session.scalar(
            select(func.count())
            .select_from(ChangeRecord)
            .where(ChangeRecord.review_status == ChangeReviewStatus.PENDING)
        )
        or 0
    )

    status_counts: dict[VerificationStatus, int] = {status: 0 for status in VerificationStatus}
    for entity_type in ALL_ENTITY_TYPES:
        for status, count in _verification_status_counts_for(session, entity_type):
            status_counts[status] += count

    recent_decisions = (
        session.execute(
            select(ChangeRecord)
            .where(ChangeRecord.review_status != ChangeReviewStatus.PENDING)
            .order_by(ChangeRecord.detected_at.desc())
            .limit(recent_limit)
        )
        .scalars()
        .all()
    )

    recent_verifications = (
        session.execute(
            select(VerificationRecord)
            .order_by(VerificationRecord.verified_at.desc().nullslast())
            .limit(recent_limit)
        )
        .scalars()
        .all()
    )

    return DashboardMetrics(
        pending_change_records=pending_count,
        verification_status_counts=status_counts,
        recent_change_decisions=list(recent_decisions),
        recent_verifications=list(recent_verifications),
    )
