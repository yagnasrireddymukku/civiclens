"""Turns tracked state into `Notification` rows — three independent
generators, one per `NotificationType` (this phase's explicit "keep...
notification generation... as a separate responsibility" from
tracking/change-detection/delivery). Each is idempotent via
`app.notifications.service.create_notification`'s dedup-key insert —
calling any of them twice in a row (or after a partial failure)
produces zero duplicate rows.

None of these ever fabricates a fact: deadline reminders only fire for
a real, structured deadline (`app.tracking.deadlines`); change
notifications only fire for an **approved** `ChangeRecord`
(`review_status == APPROVED` — never `PENDING`/`REJECTED`, this phase's
explicit "do not generate notifications based on unverified
information"); unavailability notifications only fire once
`search_documents` no longer has the entity, the same trust gate every
other Phase 12 retrieval path already relies on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.notifications.enums import NotificationType
from app.notifications.service import create_notification
from app.search.models import SearchDocument
from app.sources.enums import ChangeReviewStatus
from app.sources.models import ChangeRecord
from app.tracking.deadlines import get_deadline_for_entity, is_expired, time_to_deadline
from app.tracking.enums import TrackedEntityType
from app.tracking.models import TrackedItem
from app.tracking.service import entity_type_and_id

_FIELD_LABELS = {
    "publication_status": "Publication status",
    "deadline": "Application deadline",
}


@dataclass(frozen=True, slots=True)
class GenerationSummary:
    deadline_reminders: int
    change_notifications: int
    unavailability_notifications: int


def generate_deadline_reminders(
    session: Session, *, reminder_days_before: int, now: datetime
) -> int:
    created = 0
    active_items = session.query(TrackedItem).filter(TrackedItem.is_active.is_(True)).all()
    for item in active_items:
        entity_type, entity_id = entity_type_and_id(item)
        deadline = get_deadline_for_entity(session, entity_type, entity_id)
        if deadline is None or is_expired(deadline, now=now):
            continue
        if time_to_deadline(deadline, now=now) > timedelta(days=reminder_days_before):
            continue

        dedup_key = f"DEADLINE_REMINDER:{entity_type.value}:{entity_id}:{deadline.isoformat()}"
        result = create_notification(
            session,
            user_id=item.user_id,
            notification_type=NotificationType.DEADLINE_REMINDER,
            title="Deadline approaching",
            body=(
                f"A {entity_type.value} you're tracking has an application deadline on "
                f"{deadline.isoformat()}."
            ),
            dedup_key=dedup_key,
            entity_type=entity_type.value,
            entity_id=entity_id,
        )
        if result is not None:
            created += 1
    return created


def generate_change_notifications(session: Session) -> int:
    created = 0
    approved_changes = (
        session.query(ChangeRecord)
        .filter(ChangeRecord.review_status == ChangeReviewStatus.APPROVED)
        .all()
    )
    for change in approved_changes:
        try:
            entity_type = TrackedEntityType(change.entity_type)
        except ValueError:
            # A change record for an entity type this domain doesn't
            # track (e.g. a future ingestion pipeline covering exams) —
            # not this generator's concern, skip rather than crash.
            continue

        column_name = f"{entity_type.value}_id"
        tracked_items = (
            session.query(TrackedItem)
            .filter(
                getattr(TrackedItem, column_name) == change.entity_id,
                TrackedItem.is_active.is_(True),
            )
            .all()
        )
        if not tracked_items:
            continue

        field_label = _FIELD_LABELS.get(change.field, change.field)
        body = f"{field_label} changed from {change.old_value!r} to {change.new_value!r}."
        for item in tracked_items:
            dedup_key = f"CHANGE_DETECTED:{change.id}:{item.user_id}"
            result = create_notification(
                session,
                user_id=item.user_id,
                notification_type=NotificationType.CHANGE_DETECTED,
                title=f"Update: {field_label.lower()} changed",
                body=body,
                dedup_key=dedup_key,
                entity_type=change.entity_type,
                entity_id=change.entity_id,
                change_record_id=change.id,
            )
            if result is not None:
                created += 1
    return created


def generate_unavailability_notifications(session: Session, *, locale: str = "en") -> int:
    created = 0
    active_items = session.query(TrackedItem).filter(TrackedItem.is_active.is_(True)).all()
    for item in active_items:
        entity_type, entity_id = entity_type_and_id(item)
        still_visible = (
            session.query(SearchDocument)
            .filter_by(entity_type=entity_type.value, entity_id=entity_id, locale=locale)
            .one_or_none()
        )
        if still_visible is not None:
            continue

        dedup_key = f"ENTITY_NO_LONGER_AVAILABLE:{entity_type.value}:{entity_id}"
        result = create_notification(
            session,
            user_id=item.user_id,
            notification_type=NotificationType.ENTITY_NO_LONGER_AVAILABLE,
            title="No longer available",
            body=(
                f"A {entity_type.value} you were tracking is no longer published on "
                "CivicLens. It may have expired, been withdrawn, or been removed."
            ),
            dedup_key=dedup_key,
            entity_type=entity_type.value,
            entity_id=entity_id,
        )
        if result is not None:
            created += 1
    return created
