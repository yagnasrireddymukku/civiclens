"""Change detection — this phase's §4.4. Reuses the existing
`app.sources.models.ChangeRecord` (Phase 3), never instantiated by any
module until this one — no ingestion pipeline exists yet (Admin
Intelligence Center, still unbuilt), so this is the first real producer
of `ChangeRecord` rows in this codebase.

**Stable field-level comparison, not "did anything change"**: only a
small, named set of fields per entity type is compared
(`_SUPPORTED_FIELDS`) — `publication_status` and, where the entity type
has one, its structured deadline date. Re-indexing, a touched
`updated_at`, or reformatted prose never produces a `ChangeRecord`,
because none of those are read here at all (this phase's explicit "do
not generate notifications merely because... its content was
reformatted").

**Never auto-approved.** Every detected change is recorded with
`review_status=PENDING` (`ChangeRecord`'s own existing default) —
exactly this phase's explicit "do not implement... automatic approval
of changes." `approve_change_record`/`reject_change_record` below are
the smallest capability a future Admin Intelligence Center review UI
(still unbuilt) would call; neither is exposed as an HTTP endpoint this
phase (no auth/role-check for `editor`/`admin` exists to gate one yet —
`app.auth`'s `UserRole` enum has the values, but no route uses
`require_role` anywhere in this codebase).

**Idempotent by construction**: the "current" value of a field is
compared against the `new_value` of the most recent prior
`ChangeRecord` for that exact `(entity_type, entity_id, field)` —
running detection twice in a row with nothing having changed produces
zero new rows, since the second run's "current" already equals the
first run's recorded `new_value`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.documents.models import CivicDocument
from app.jobs.models import Job
from app.schemes.models import Scheme
from app.services.models import Service
from app.sources.enums import ChangeReviewStatus
from app.sources.models import ChangeRecord
from app.tracking.deadlines import get_deadline_for_entity
from app.tracking.enums import TrackedEntityType

FIELD_PUBLICATION_STATUS = "publication_status"
FIELD_DEADLINE = "deadline"

_SUPPORTED_FIELDS: dict[TrackedEntityType, tuple[str, ...]] = {
    TrackedEntityType.JOB: (FIELD_PUBLICATION_STATUS, FIELD_DEADLINE),
    TrackedEntityType.SCHEME: (FIELD_PUBLICATION_STATUS, FIELD_DEADLINE),
    TrackedEntityType.SERVICE: (FIELD_PUBLICATION_STATUS,),
    TrackedEntityType.DOCUMENT: (FIELD_PUBLICATION_STATUS,),
}


def _current_field_values(
    session: Session, entity_type: TrackedEntityType, entity_id: uuid.UUID
) -> dict[str, str | None] | None:
    """`None` when the entity no longer exists at all — distinct from a
    field being `None` (e.g. no deadline stated)."""

    values: dict[str, str | None] = {}
    if entity_type == TrackedEntityType.JOB:
        job = session.get(Job, entity_id)
        if job is None:
            return None
        values[FIELD_PUBLICATION_STATUS] = job.publication_status.value
    elif entity_type == TrackedEntityType.SCHEME:
        scheme = session.get(Scheme, entity_id)
        if scheme is None:
            return None
        values[FIELD_PUBLICATION_STATUS] = scheme.publication_status.value
    elif entity_type == TrackedEntityType.SERVICE:
        service = session.get(Service, entity_id)
        if service is None:
            return None
        values[FIELD_PUBLICATION_STATUS] = service.publication_status.value
    elif entity_type == TrackedEntityType.DOCUMENT:
        document = session.get(CivicDocument, entity_id)
        if document is None:
            return None
        values[FIELD_PUBLICATION_STATUS] = document.publication_status.value
    else:  # pragma: no cover - TrackedEntityType is exhaustively handled above
        raise AssertionError(f"unreachable entity_type {entity_type}")

    if FIELD_DEADLINE in _SUPPORTED_FIELDS[entity_type]:
        deadline = get_deadline_for_entity(session, entity_type, entity_id)
        values[FIELD_DEADLINE] = deadline.isoformat() if deadline else None
    return values


def detect_changes(
    session: Session, *, entity_type: TrackedEntityType, entity_id: uuid.UUID
) -> list[ChangeRecord]:
    current = _current_field_values(session, entity_type, entity_id)
    if current is None:
        return []

    created: list[ChangeRecord] = []
    now = datetime.now(UTC)
    for field, new_value in current.items():
        last = (
            session.query(ChangeRecord)
            .filter_by(entity_type=entity_type.value, entity_id=entity_id, field=field)
            .order_by(ChangeRecord.detected_at.desc())
            .first()
        )
        baseline = last.new_value if last is not None else None
        if new_value == baseline:
            continue
        record = ChangeRecord(
            entity_type=entity_type.value,
            entity_id=entity_id,
            field=field,
            old_value=baseline,
            new_value=new_value,
            detected_at=now,
            review_status=ChangeReviewStatus.PENDING,
        )
        session.add(record)
        session.flush()
        created.append(record)
    return created


def approve_change_record(
    session: Session, *, change_record_id: uuid.UUID, reviewed_by: uuid.UUID | None = None
) -> ChangeRecord:
    """The smallest capability a future admin review UI would call —
    see module docstring. Not exposed as a route this phase."""

    record = session.get(ChangeRecord, change_record_id)
    if record is None:
        raise ValueError(f"No such change record: {change_record_id}")
    record.review_status = ChangeReviewStatus.APPROVED
    record.reviewed_by = reviewed_by
    record.applied_at = datetime.now(UTC)
    return record


def reject_change_record(
    session: Session, *, change_record_id: uuid.UUID, reviewed_by: uuid.UUID | None = None
) -> ChangeRecord:
    record = session.get(ChangeRecord, change_record_id)
    if record is None:
        raise ValueError(f"No such change record: {change_record_id}")
    record.review_status = ChangeReviewStatus.REJECTED
    record.reviewed_by = reviewed_by
    return record
