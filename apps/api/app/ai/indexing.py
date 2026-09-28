"""Knowledge-chunk indexing — the only write path onto
`ai_knowledge_chunks`, mirroring `app.search.service`'s "one module owns
all writes" convention.

`search_documents` is the enumeration source (this phase's reuse
decision, docs/DATABASE.md §16): whatever is currently visible there —
already `VERIFIED`/`NEEDS_REVIEW`-only, already excluding
`UNVERIFIED`/`EXPIRED`/unpublished/soft-deleted entities — is exactly
the set eligible for RAG indexing too. No separate "is this entity
allowed to be indexed" check is re-implemented here.

Idempotent by content hash (this phase's §7): re-running `reindex_all`
against unchanged entities calls the embedding provider zero times.
Orphaned chunks (an entity that was indexed before but has since been
unpublished/removed from `search_documents`) are deleted outright here
too — belt-and-suspenders alongside the join-based trust gate
`app.ai.retrieval` already relies on (see `app.ai.models.KnowledgeChunk`'s
module docstring), not a substitute for it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ai.chunking import build_chunk_text, content_hash
from app.ai.enums import AIEntityType
from app.ai.models import KnowledgeChunk
from app.ai.providers import EmbeddingProvider, EmbeddingProviderError
from app.search.models import SearchDocument


@dataclass(frozen=True, slots=True)
class IndexOutcome:
    entity_type: str
    entity_id: uuid.UUID
    locale: str
    status: str  # "indexed" | "skipped_unchanged" | "removed" | "failed"


async def index_one(
    session: Session,
    *,
    entity_type: AIEntityType,
    entity_id: uuid.UUID,
    locale: str,
    embedding_provider: EmbeddingProvider,
) -> IndexOutcome:
    """Builds/re-embeds exactly one entity's chunk. Raises
    `EmbeddingProviderError` on provider failure — callers doing a bulk
    run catch this per-entity so one failing entity doesn't abort the
    whole reindex (see `reindex_all`)."""

    text = build_chunk_text(session, entity_type, entity_id)
    if text is None:
        return IndexOutcome(entity_type.value, entity_id, locale, "removed")

    new_hash = content_hash(text)
    existing = session.execute(
        select(KnowledgeChunk.content_hash, KnowledgeChunk.embedding_model).where(
            KnowledgeChunk.entity_type == entity_type.value,
            KnowledgeChunk.entity_id == entity_id,
            KnowledgeChunk.locale == locale,
            KnowledgeChunk.chunk_index == 0,
        )
    ).first()
    if existing is not None and existing[0] == new_hash and existing[1] == embedding_provider.model:
        return IndexOutcome(entity_type.value, entity_id, locale, "skipped_unchanged")

    result = await embedding_provider.embed([text])
    (vector,) = result.vectors

    stmt = pg_insert(KnowledgeChunk).values(
        entity_type=entity_type.value,
        entity_id=entity_id,
        locale=locale,
        chunk_index=0,
        chunk_text=text,
        content_hash=new_hash,
        embedding_model=result.model,
        embedding_dimensions=result.dimensions,
        embedding=vector,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_ai_knowledge_chunks_entity_locale_chunk",
        set_={
            "chunk_text": stmt.excluded.chunk_text,
            "content_hash": stmt.excluded.content_hash,
            "embedding_model": stmt.excluded.embedding_model,
            "embedding_dimensions": stmt.excluded.embedding_dimensions,
            "embedding": stmt.excluded.embedding,
            "updated_at": func.now(),
        },
    )
    session.execute(stmt)
    return IndexOutcome(entity_type.value, entity_id, locale, "indexed")


def _remove_orphaned_chunks(session: Session) -> int:
    """Deletes any `ai_knowledge_chunks` row whose (entity_type,
    entity_id, locale) no longer has a matching `search_documents` row —
    an entity that was unpublished/expired/deleted since the last
    reindex."""

    live_keys = select(
        SearchDocument.entity_type, SearchDocument.entity_id, SearchDocument.locale
    ).subquery()
    orphaned = (
        select(KnowledgeChunk.id)
        .outerjoin(
            live_keys,
            (KnowledgeChunk.entity_type == live_keys.c.entity_type)
            & (KnowledgeChunk.entity_id == live_keys.c.entity_id)
            & (KnowledgeChunk.locale == live_keys.c.locale),
        )
        .where(live_keys.c.entity_type.is_(None))
    )
    orphaned_ids = [row[0] for row in session.execute(orphaned).all()]
    if not orphaned_ids:
        return 0
    session.query(KnowledgeChunk).filter(KnowledgeChunk.id.in_(orphaned_ids)).delete(
        synchronize_session=False
    )
    return len(orphaned_ids)


@dataclass(frozen=True, slots=True)
class ReindexSummary:
    indexed: int
    skipped_unchanged: int
    removed: int
    failed: int


async def reindex_all(session: Session, *, embedding_provider: EmbeddingProvider) -> ReindexSummary:
    """Rebuilds every knowledge chunk for every entity currently in
    `search_documents`. Intended for a manual ops script
    (`scripts/reindex_ai_knowledge.py`) or a future authenticated admin
    action — never an unauthenticated HTTP route (no auth/role-check
    mechanism exists anywhere in this codebase yet, verified by hand;
    see docs/AI_ARCHITECTURE.md §9's explicit note on this)."""

    entities = session.execute(
        select(SearchDocument.entity_type, SearchDocument.entity_id, SearchDocument.locale)
    ).all()

    indexed = skipped = failed = 0
    for entity_type_value, entity_id, locale in entities:
        try:
            entity_type = AIEntityType(entity_type_value)
        except ValueError:
            # A future domain's entity_type not yet wired into
            # app.ai.chunking's `_BUILDERS` — skip, don't crash the
            # whole reindex over content this module doesn't know how
            # to chunk yet.
            failed += 1
            continue
        try:
            outcome = await index_one(
                session,
                entity_type=entity_type,
                entity_id=entity_id,
                locale=locale,
                embedding_provider=embedding_provider,
            )
        except EmbeddingProviderError:
            failed += 1
            continue
        if outcome.status == "indexed":
            indexed += 1
        elif outcome.status == "skipped_unchanged":
            skipped += 1

    removed = _remove_orphaned_chunks(session)
    session.commit()
    return ReindexSummary(
        indexed=indexed, skipped_unchanged=skipped, removed=removed, failed=failed
    )
