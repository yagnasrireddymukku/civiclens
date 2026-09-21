"""Provenance: Source, SourceVersion, VerificationRecord, ChangeRecord —
see docs/DATABASE.md §2.7, docs/DATA_GOVERNANCE.md, ADR-008.

This is cross-cutting infrastructure every future fact-bearing domain
(jobs, schemes, representatives, ...) will reference, not a domain of its
own — see docs/ARCHITECTURE.md §6, which lists `sources/` as a sibling
module to the domain modules for exactly this reason.

`entity_type`/`entity_id` on VerificationRecord and ChangeRecord form a
polymorphic reference to whichever fact-bearing row is being verified or
changed. `entity_type` is a plain, indexed string column rather than a
database enum: Phase 3 has no domain tables yet to enumerate (jobs,
schemes, etc. arrive in docs/ROADMAP.md Phases 6-9), and hardcoding an
enum here would need editing on every future domain phase. Validating
`entity_type` against real, existing entity types is that future phase's
responsibility when it starts writing these rows — not this module's,
which cannot know the valid set yet without importing domain modules that
don't exist.

Geography (State/District/Constituency) deliberately does not carry a
direct `source_id`: docs/DATABASE.md §2.1 does not list one, treating
geography as administrative reference data rather than an evolving fact.
That is a docs/DATABASE.md-level decision, not something changed here.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.sources.enums import ChangeReviewStatus, VerificationStatus


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The authoritative/external origin of a fact. See
    docs/DATA_GOVERNANCE.md §3 for the required-fields rationale."""

    __tablename__ = "sources"

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    organization: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    retrieved_date: Mapped[date] = mapped_column(Date, nullable=False)

    versions: Mapped[list[SourceVersion]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class SourceVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A captured snapshot of a source's content at a point in time —
    change detection (docs/DATA_SOURCES.md §5) diffs against this."""

    __tablename__ = "source_versions"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    snapshot_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source: Mapped[Source] = relationship(back_populates="versions")


class VerificationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Evidence that a CivicLens fact was reviewed/verified against a
    source. See docs/DATA_GOVERNANCE.md §4 for the four-state model."""

    __tablename__ = "verification_records"

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status", native_enum=True),
        nullable=False,
        default=VerificationStatus.UNVERIFIED,
        index=True,
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped[Source] = relationship()


class ChangeRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audit trail entry for a detected change to a fact-bearing entity —
    the non-optional trail required by docs/DATA_GOVERNANCE.md §8 and
    docs/PRODUCT_REQUIREMENTS.md NFR-A1. Never overwritten in place."""

    __tablename__ = "change_records"

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    # Free-form text: the field being changed varies by entity/column type
    # (a date, a string, a number) — a generic audit trail stores the
    # rendered value, not a typed one. See docs/DATABASE.md §2.7.
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    review_status: Mapped[ChangeReviewStatus] = mapped_column(
        Enum(ChangeReviewStatus, name="change_review_status", native_enum=True),
        nullable=False,
        default=ChangeReviewStatus.PENDING,
        index=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_version: Mapped[SourceVersion | None] = relationship()
