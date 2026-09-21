"""SearchDocument — the search-document representation described in
docs/SEARCH.md and this phase's kickoff §4-5.

Deliberately NOT a set of `tsvector` columns bolted onto future domain
tables (jobs, schemes, ...): those tables don't exist yet
(docs/ROADMAP.md Phases 6-9), and this phase's own instructions say not
to create artificial production domain tables merely for search. Instead:

    DOMAIN DATA (future)  --[index builder, app/search/service.py]-->
    SearchDocument (this table)  --[tsvector + pg_trgm indexes]-->
    SEARCH INDEX  --[GET /api/v1/search]--> RANKED RESULTS

`SearchDocument` is the stable "search document representation" future
domain modules will write into via `service.upsert_search_document`, so
they never couple themselves to Postgres search internals directly (this
phase's §4). It is a pure read-side projection
(docs/SEARCH.md §1): entity_type/entity_id is a polymorphic reference to
whatever future domain row this document represents (no FK — the same
documented tradeoff as `app/sources/models.py`'s VerificationRecord/
ChangeRecord), so this table can be dropped and rebuilt from source
tables at any time with no data loss.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.sources.enums import VerificationStatus


class SearchDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "search_documents"
    __table_args__ = (
        UniqueConstraint(
            "entity_type", "entity_id", "locale", name="uq_search_documents_entity_locale"
        ),
        Index("ix_search_documents_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_search_documents_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )

    # Polymorphic reference to the future domain row this document
    # represents — see module docstring for why there is no FK.
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    # BCP-47-ish locale tag; only "en"/"te" are meaningful today
    # (docs/ARCHITECTURE.md §10) but this column isn't a DB enum, so a
    # future locale is a data change, not a migration.
    locale: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Additional free-text content (e.g. a longer description) folded
    # into the search vector at lower weight than title/summary.
    searchable_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The public route this result links to, e.g. "/jobs/test-job-001" —
    # locale-prefixed routing (docs/FRONTEND.md §7) is applied by the
    # frontend, not stored here.
    route: Mapped[str] = mapped_column(String(500), nullable=False)

    state_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("states.id", ondelete="SET NULL"), nullable=True, index=True
    )
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Provenance must survive into search results (this phase's §13,
    # docs/DATA_GOVERNANCE.md §3) — required, not optional.
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Denormalized copy of the current verification state (rather than a
    # join to verification_records on every search query) — consistent
    # with this table being a full read-side projection
    # (docs/SEARCH.md §1): everything a result card needs to render is
    # already here. Only VERIFIED/NEEDS_REVIEW documents are ever written
    # here at all (docs/SEARCH.md §3) — enforced by `service.py`, not by
    # a DB constraint, since UNVERIFIED/EXPIRED simply means "don't index
    # this," not "index it with a different status."
    # postgresql.ENUM (dialect-specific), not the generic sa.Enum: the
    # generic type's create_type=False does not reliably suppress a
    # duplicate CREATE TYPE when Alembic's autogenerate later compares
    # this model against the DB — verified by hand (see the migration
    # this table first appeared in for the concrete failure). The
    # dialect-specific ENUM's create_type is what Alembic's DDL path
    # actually honors.
    verification_status: Mapped[VerificationStatus] = mapped_column(
        postgresql.ENUM(VerificationStatus, name="verification_status", create_type=False),
        nullable=False,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Populated by service.upsert_search_document via a weighted
    # to_tsvector/setweight expression — never written to directly, and
    # never a DB-generated column (see service.py for why: the weighting
    # config depends on `locale`, computed in one place, testable in
    # Python rather than embedded in DDL).
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
