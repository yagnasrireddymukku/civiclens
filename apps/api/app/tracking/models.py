"""`TrackedItem` — one user's subscription to one supported entity. See
docs/DATABASE.md §17 for the full architectural writeup; summarized
here:

**Four nullable FKs, not a polymorphic reference** — the opposite
choice from Phase 12's `ai_knowledge_chunks`, the same choice as Phase
11's `EligibilityRule`. This phase's kickoff fixes the entity set at
exactly four (jobs, services, schemes, documents — scholarships tracked
via their parent `scheme_id`), and a dangling tracked item pointing at
a deleted entity would be a real, visible dashboard bug (a broken link
on a user's personal page) that real `ON DELETE CASCADE` referential
integrity prevents for free. Phase 12's opposite reasoning (avoid
forcing a costly recompute on cascade) doesn't apply here — deleting a
`TrackedItem` row costs nothing to "recompute."

**Duplicate-active-tracking prevention** is a `UNIQUE ... NULLS NOT
DISTINCT` constraint (Postgres 16, verified available in this project's
actual environment) across all four FK columns plus `user_id` — with
`NULLS NOT DISTINCT`, two rows that are both `(user, job=X, NULL, NULL,
NULL)` collide as true duplicates (Postgres's *default* NULL-handling
would treat every NULL as unique-from-every-other-NULL, which would
silently defeat a plain `UNIQUE` constraint on a mostly-NULL column set
— verified by hand before choosing this, not assumed). This directly
satisfies this phase's "prevent duplicate active tracking records for
the same user and entity" requirement at the database layer, not only
in application code.

**Pause vs. remove are two different operations on purpose** (this
phase's §4.1: "adding, listing, pausing/resuming..., and removing").
Removing is a hard `DELETE` (frees the row for a future re-track of the
same entity). Pausing is a soft `is_active=False` toggle on the *same*
row — re-tracking an already-tracked (even paused) entity is idempotent:
it reactivates the existing row rather than erroring or duplicating.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TrackedItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tracked_items"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(job_id, service_id, scheme_id, document_id) = 1",
            name="ck_tracked_items_exactly_one_entity",
        ),
        UniqueConstraint(
            "user_id",
            "job_id",
            "service_id",
            "scheme_id",
            "document_id",
            name="uq_tracked_items_user_entity",
            postgresql_nulls_not_distinct=True,
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True
    )
    scheme_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("civic_documents.id", ondelete="CASCADE"), nullable=True, index=True
    )

    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
