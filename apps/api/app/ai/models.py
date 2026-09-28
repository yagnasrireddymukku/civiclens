"""`KnowledgeChunk` — the RAG retrieval substrate, docs/AI_ARCHITECTURE.md
§3 realized. See docs/DATABASE.md §16 for the full architectural
writeup; summarized here:

**Polymorphic `entity_type`/`entity_id`/`locale`, not a real FK** —
deliberately the opposite choice from Phase 11's `EligibilityRule`
(three real FKs for a small, fixed entity set). This table follows
`app.search.models.SearchDocument`'s established precedent instead
(itself following `VerificationRecord`/`ChangeRecord`'s precedent): a
plain, indexed `(entity_type, entity_id, locale)` key, not a foreign
key. Two independent reasons: (1) the entity-type set here is the same
open-ended "any current or future fact-bearing domain" set
`SearchDocument` already serves, not Phase 11's fixed three; (2) FK'ing
to `search_documents.id` specifically was considered and rejected —
`search_documents` is explicitly documented as droppable/rebuildable at
any time "with no data loss" (its own module docstring), and cascading
that drop onto every embedding would force a full, costly re-embedding
of everything on what is meant to be a cheap, lossless operation. A
plain shared key lets retrieval `JOIN` the two tables (see
`app.ai.retrieval`) without coupling either table's lifecycle to the
other's.

**No `source_id`/`verification_status`/`route` columns here** —
retrieval always joins to `search_documents` (same `entity_type`/
`entity_id`/`locale`) to get them. This is the trust gate, not a
duplicated one: a chunk whose entity is no longer in `search_documents`
(unpublished, expired, or never re-indexed after a status change)
simply cannot be retrieved — an `INNER JOIN` filters it out
automatically, the same way `VERIFIED`/`NEEDS_REVIEW`-only membership in
`search_documents` already gates ordinary search results.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ARRAY, CheckConstraint, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_knowledge_chunks"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "locale",
            "chunk_index",
            name="uq_ai_knowledge_chunks_entity_locale_chunk",
        ),
        CheckConstraint(
            "array_length(embedding, 1) = embedding_dimensions",
            name="ck_ai_knowledge_chunks_embedding_length_matches_dimensions",
        ),
    )

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    # One chunk per entity today (this phase's deliberate MVP scope —
    # deterministic, no chunk-boundary/overlap logic to get subtly
    # wrong); `chunk_index` exists so a future multi-chunk-per-entity
    # split needs a chunking-logic change, not a migration.
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    # sha256 hex digest of `chunk_text` — lets re-indexing skip an
    # unchanged entity without re-calling the embedding provider (this
    # phase's explicit cost-control requirement: "avoid unnecessary
    # embedding regeneration").
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Recorded per row, not just in config, so retrieval can filter to
    # only the currently-configured model/dimensions (the "safe
    # compatibility check" this phase requires) even if
    # AI_EMBEDDING_MODEL changes without every row being re-indexed
    # first — old rows become invisible to semantic search rather than
    # corrupting a similarity comparison across incompatible vectors.
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)

    # No pgvector in this project's actual local/test PostgreSQL
    # distribution (verified by hand — no `vector.control` present, and
    # this environment has no Docker either) — see docs/DATABASE.md §16
    # for the full disclosed deviation from ADR-006's pgvector
    # aspiration. A plain float array with a length-matches-dimensions
    # CHECK constraint, similarity computed in Python
    # (`app.ai.retrieval`) — adequate at this project's actual current
    # scale (fixture-only content, no real government data permitted
    # before Phase 13), swappable for a real `vector(N)` column and an
    # in-database `<=>` query later without changing this table's
    # conceptual shape or any caller's function signature.
    embedding: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
