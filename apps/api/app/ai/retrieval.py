"""Retrieval — the only place a citation's underlying evidence is looked
up. Both paths below `JOIN` (implicitly or explicitly) against
`search_documents`, so an entity that isn't currently `VERIFIED`/
`NEEDS_REVIEW`-published there is never retrievable here either, no
matter what `ai_knowledge_chunks` still holds (see
`app.ai.models.KnowledgeChunk`'s module docstring).

Two paths, matching this phase's §6 ("use the established PostgreSQL
search as a lexical retrieval path and assess hybrid retrieval where
useful"):

- **Lexical**: reuses `app.search.service.search_documents` verbatim —
  the exact ranking/typo-tolerance logic every browse/search page
  already depends on, not a second implementation of full-text search.
- **Semantic**: cosine similarity over `ai_knowledge_chunks.embedding`,
  computed in Python (no pgvector in this environment — see
  `app.ai.models.KnowledgeChunk`'s module docstring for the disclosed
  deviation), filtered to the *currently configured* embedding model/
  dimensions only (the "safe compatibility check" this phase requires).

`hybrid_retrieve` runs both (semantic only if an embedding provider is
configured) and merges by entity, keeping the higher score — never both
scores summed, which would make ranking depend on which path happened to
also match rather than genuine relevance.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.enums import RetrievalMatchType
from app.ai.models import KnowledgeChunk
from app.search import service as search_service
from app.search.models import SearchDocument
from app.sources.enums import VerificationStatus
from app.sources.models import Source

# Bounds the semantic path's candidate scan — adequate at this project's
# actual current scale (fixture-only content; no real government data
# permitted before Phase 13, docs/DATA_SOURCES.md) and an honest,
# documented limitation rather than a claim of production-scale
# performance (this phase's explicit instruction). Revisit once pgvector
# (or real content volume) makes an in-database nearest-neighbor query
# worth the migration.
_SEMANTIC_CANDIDATE_CAP = 500


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    entity_type: str
    entity_id: uuid.UUID
    chunk_text: str
    title: str
    route: str
    source_organization: str
    source_title: str
    source_url: str
    verification_status: VerificationStatus
    last_verified_at: datetime | None
    score: float
    match_type: RetrievalMatchType

    @property
    def needs_review_caveat(self) -> bool:
        return self.verification_status == VerificationStatus.NEEDS_REVIEW


def lexical_retrieve(
    session: Session, *, query: str, locale: str, limit: int
) -> list[RetrievedChunk]:
    result = search_service.search_documents(
        session, q=query, locale=locale, page=1, page_size=limit
    )
    if not result.rows:
        return []

    keys = [(row.document.entity_type, row.document.entity_id, locale) for row in result.rows]
    chunk_rows = (
        session.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.locale == locale,
                KnowledgeChunk.chunk_index == 0,
                KnowledgeChunk.entity_type.in_({k[0] for k in keys}),
                KnowledgeChunk.entity_id.in_({k[1] for k in keys}),
            )
        )
        .scalars()
        .all()
    )
    chunk_by_key = {(c.entity_type, c.entity_id, c.locale): c for c in chunk_rows}

    retrieved: list[RetrievedChunk] = []
    for rank, row in enumerate(result.rows):
        key = (row.document.entity_type, row.document.entity_id, locale)
        chunk = chunk_by_key.get(key)
        if chunk is None:
            # Not yet indexed for RAG (search and RAG indexing are
            # separate steps) — skip; there's no chunk text to ground
            # an answer on, only a search snippet.
            continue
        retrieved.append(
            RetrievedChunk(
                entity_type=row.document.entity_type,
                entity_id=row.document.entity_id,
                chunk_text=chunk.chunk_text,
                title=row.document.title,
                route=row.document.route,
                source_organization=row.source.organization,
                source_title=row.source.title,
                source_url=row.source.url,
                verification_status=row.document.verification_status,
                last_verified_at=row.document.last_verified_at,
                # Rank-based score (1.0 for the top lexical result,
                # decreasing) — the search module's own rank/similarity
                # score isn't exposed per-row today, and position in an
                # already-ranked result set is a reasonable, simple,
                # deterministic proxy for this phase's merge step.
                score=1.0 - (rank * 0.05),
                match_type=RetrievalMatchType.LEXICAL,
            )
        )
    return retrieved


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_retrieve(
    session: Session,
    *,
    query_vector: list[float],
    locale: str,
    embedding_model: str,
    embedding_dimensions: int,
    limit: int,
) -> list[RetrievedChunk]:
    stmt = (
        select(KnowledgeChunk, SearchDocument, Source)
        .join(
            SearchDocument,
            (KnowledgeChunk.entity_type == SearchDocument.entity_type)
            & (KnowledgeChunk.entity_id == SearchDocument.entity_id)
            & (KnowledgeChunk.locale == SearchDocument.locale),
        )
        .join(Source, SearchDocument.source_id == Source.id)
        .where(
            KnowledgeChunk.locale == locale,
            KnowledgeChunk.chunk_index == 0,
            KnowledgeChunk.embedding_model == embedding_model,
            KnowledgeChunk.embedding_dimensions == embedding_dimensions,
        )
        .limit(_SEMANTIC_CANDIDATE_CAP)
    )
    candidates = session.execute(stmt).all()

    scored = [
        RetrievedChunk(
            entity_type=chunk.entity_type,
            entity_id=chunk.entity_id,
            chunk_text=chunk.chunk_text,
            title=document.title,
            route=document.route,
            source_organization=source.organization,
            source_title=source.title,
            source_url=source.url,
            verification_status=document.verification_status,
            last_verified_at=document.last_verified_at,
            score=_cosine_similarity(query_vector, chunk.embedding),
            match_type=RetrievalMatchType.SEMANTIC,
        )
        for chunk, document, source in candidates
    ]
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:limit]


def merge_retrieved(*chunk_lists: list[RetrievedChunk], limit: int) -> list[RetrievedChunk]:
    """De-duplicates by entity, keeping whichever occurrence scored
    higher — never summing scores across lexical/semantic matches
    (this phase's §6 hybrid-retrieval note)."""

    best: dict[tuple[str, uuid.UUID], RetrievedChunk] = {}
    for chunks in chunk_lists:
        for chunk in chunks:
            key = (chunk.entity_type, chunk.entity_id)
            existing = best.get(key)
            if existing is None or chunk.score > existing.score:
                best[key] = chunk
    merged = sorted(best.values(), key=lambda r: r.score, reverse=True)
    return merged[:limit]


def get_chunk_for_entity(
    session: Session, *, entity_type: str, entity_id: uuid.UUID, locale: str
) -> RetrievedChunk | None:
    """Direct lookup for an explicit `entity_context` hint (see
    `app.ai.service.answer_question`) — guarantees that entity's own
    chunk is considered even if the free-text question doesn't literally
    match its title/summary. Still gated by the same `search_documents`
    join: an entity that isn't currently published there returns `None`
    here too, exactly as it would from either retrieval path."""

    stmt = (
        select(KnowledgeChunk, SearchDocument, Source)
        .join(
            SearchDocument,
            (KnowledgeChunk.entity_type == SearchDocument.entity_type)
            & (KnowledgeChunk.entity_id == SearchDocument.entity_id)
            & (KnowledgeChunk.locale == SearchDocument.locale),
        )
        .join(Source, SearchDocument.source_id == Source.id)
        .where(
            KnowledgeChunk.entity_type == entity_type,
            KnowledgeChunk.entity_id == entity_id,
            KnowledgeChunk.locale == locale,
            KnowledgeChunk.chunk_index == 0,
        )
    )
    result = session.execute(stmt).first()
    if result is None:
        return None
    chunk, document, source = result
    return RetrievedChunk(
        entity_type=chunk.entity_type,
        entity_id=chunk.entity_id,
        chunk_text=chunk.chunk_text,
        title=document.title,
        route=document.route,
        source_organization=source.organization,
        source_title=source.title,
        source_url=source.url,
        verification_status=document.verification_status,
        last_verified_at=document.last_verified_at,
        score=1.0,
        match_type=RetrievalMatchType.LEXICAL,
    )
