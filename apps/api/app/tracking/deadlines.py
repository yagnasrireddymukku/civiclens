"""Deadline semantics — this phase's §4.3. Only two domains have a real
structured deadline field: `JobNotification.application_end` and
`ScholarshipDetail.application_closes` (verified by hand — `Service`
and `CivicDocument` have no structured deadline date anywhere in their
models, only free-text validity/renewal summaries). Services and plain
documents therefore never have a deadline surfaced here — `None`, never
inferred from a description field, per this phase's explicit
prohibition.

**Timezone convention, explicit and deterministic**: a deadline `Date`
(no time component, as stored) is understood as ending at 23:59:59
`Asia/Kolkata` (IST) — inclusive of the stated calendar day, in the
timezone every CivicLens deadline is actually published in. "Expired"
means strictly after that instant, computed against an explicitly
passed `now` (never `datetime.now()` read internally — see
`is_expired`'s docstring), so this stays a pure, testable function.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.jobs.models import Job
from app.schemes.models import Scheme
from app.tracking.enums import TrackedEntityType

IST = ZoneInfo("Asia/Kolkata")


def deadline_end_instant(deadline_date: date) -> datetime:
    """The exact instant a deadline date's window closes — 23:59:59 IST
    on the stated day, i.e. inclusive of the whole day."""

    return datetime.combine(deadline_date, time(23, 59, 59), tzinfo=IST)


def is_expired(deadline_date: date, *, now: datetime) -> bool:
    """`now` must be explicitly passed (tz-aware) — never read from the
    wall clock inside this function, so deadline-boundary tests are
    exact and reproducible rather than depending on when the test
    happens to run."""

    return now > deadline_end_instant(deadline_date)


def time_to_deadline(deadline_date: date, *, now: datetime) -> timedelta:
    """Positive when the deadline is still ahead, negative once expired
    (never clamped to zero — callers that need "expired" as a boolean
    use `is_expired` instead of inferring it from the sign here, since a
    zero-clamped value can't be told apart from "due right now")."""

    return deadline_end_instant(deadline_date) - now


def get_deadline_for_entity(
    session: Session, entity_type: TrackedEntityType, entity_id: uuid.UUID
) -> date | None:
    """`None` when the entity has no real, structured deadline —
    either because this entity type never has one (Service, Document),
    the entity no longer exists, or no notification/scholarship-detail
    row happens to state one. Never a guessed or descriptive-text-derived
    date (this phase's explicit prohibition)."""

    if entity_type == TrackedEntityType.JOB:
        job = session.get(Job, entity_id)
        if job is None:
            return None
        # The furthest-future stated deadline among this job's
        # notifications — a job can have several recruitment cycles
        # over time, and a later cycle's deadline is later in real
        # calendar time than an earlier one's, which is a more robust
        # "which cycle is current" signal than `created_at` (rows
        # inserted in the same database transaction can share an
        # identical `now()`-derived `created_at`, verified by hand —
        # Postgres's `now()` is transaction time, not statement time).
        deadlines = [n.application_end for n in job.notifications if n.application_end is not None]
        return max(deadlines) if deadlines else None
    if entity_type == TrackedEntityType.SCHEME:
        scheme = session.get(Scheme, entity_id)
        if scheme is None or scheme.scholarship_detail is None:
            return None
        return scheme.scholarship_detail.application_closes
    return None


@dataclass(frozen=True, slots=True)
class DeadlineInfo:
    deadline_date: date
    is_expired: bool
    time_remaining: timedelta
