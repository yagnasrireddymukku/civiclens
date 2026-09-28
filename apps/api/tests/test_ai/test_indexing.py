"""Indexing tests: idempotent re-indexing by content hash, embedding
provider failure handling, and orphaned-chunk removal when an entity
drops out of `search_documents` — docs/AI_ARCHITECTURE.md §7/§9's
"make re-indexing idempotent" and "avoid unnecessary embedding
regeneration" requirements.
"""

import asyncio
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.enums import AIEntityType
from app.ai.indexing import index_one, reindex_all
from app.ai.models import KnowledgeChunk
from app.ai.providers import EmbeddingProviderError
from app.jobs.service import sync_job_search_index
from tests.test_ai._helpers import FakeEmbeddingProvider
from tests.test_documents._helpers import make_organization, make_source, make_state
from tests.test_jobs._helpers import make_job


def _sync(coro):
    return asyncio.run(coro)


def test_index_one_creates_a_chunk_with_matching_embedding(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    sync_job_search_index(db_session, job)
    provider = FakeEmbeddingProvider(dimensions=8)

    outcome = _sync(
        index_one(
            db_session,
            entity_type=AIEntityType.JOB,
            entity_id=job.id,
            locale="en",
            embedding_provider=provider,
        )
    )

    assert outcome.status == "indexed"
    chunk = db_session.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.entity_id == job.id)
    ).scalar_one()
    assert chunk.embedding_model == provider.model
    assert chunk.embedding_dimensions == 8
    assert len(chunk.embedding) == 8
    assert provider.calls == [[chunk.chunk_text]]


def test_index_one_skips_unchanged_content_without_calling_provider(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    sync_job_search_index(db_session, job)
    provider = FakeEmbeddingProvider(dimensions=8)

    _sync(
        index_one(
            db_session,
            entity_type=AIEntityType.JOB,
            entity_id=job.id,
            locale="en",
            embedding_provider=provider,
        )
    )
    assert len(provider.calls) == 1

    second_outcome = _sync(
        index_one(
            db_session,
            entity_type=AIEntityType.JOB,
            entity_id=job.id,
            locale="en",
            embedding_provider=provider,
        )
    )

    assert second_outcome.status == "skipped_unchanged"
    assert len(provider.calls) == 1  # provider never called a second time


def test_index_one_reembeds_when_content_changes(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    sync_job_search_index(db_session, job)
    provider = FakeEmbeddingProvider(dimensions=8)

    _sync(
        index_one(
            db_session,
            entity_type=AIEntityType.JOB,
            entity_id=job.id,
            locale="en",
            embedding_provider=provider,
        )
    )
    job.summary = "An updated summary that changes the chunk text."
    db_session.flush()

    outcome = _sync(
        index_one(
            db_session,
            entity_type=AIEntityType.JOB,
            entity_id=job.id,
            locale="en",
            embedding_provider=provider,
        )
    )

    assert outcome.status == "indexed"
    assert len(provider.calls) == 2


def test_index_one_removed_for_deleted_entity(db_session: Session) -> None:
    provider = FakeEmbeddingProvider(dimensions=8)
    outcome = _sync(
        index_one(
            db_session,
            entity_type=AIEntityType.JOB,
            entity_id=uuid.uuid4(),
            locale="en",
            embedding_provider=provider,
        )
    )
    assert outcome.status == "removed"
    assert provider.calls == []


def test_index_one_propagates_provider_error(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    sync_job_search_index(db_session, job)
    provider = FakeEmbeddingProvider(dimensions=8, raise_error=True)

    with pytest.raises(EmbeddingProviderError):
        _sync(
            index_one(
                db_session,
                entity_type=AIEntityType.JOB,
                entity_id=job.id,
                locale="en",
                embedding_provider=provider,
            )
        )


def test_reindex_all_indexes_every_visible_entity_and_removes_orphans(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    sync_job_search_index(db_session, job)
    provider = FakeEmbeddingProvider(dimensions=8)

    summary = _sync(reindex_all(db_session, embedding_provider=provider))
    assert summary.indexed == 1
    assert summary.removed == 0

    # Unpublish the job (removes it from search_documents) and reindex
    # again — its now-orphaned chunk must be deleted, not left behind.
    from app.jobs.enums import JobPublicationStatus

    job.publication_status = JobPublicationStatus.DRAFT
    db_session.flush()
    sync_job_search_index(db_session, job)

    summary_after = _sync(reindex_all(db_session, embedding_provider=provider))
    assert summary_after.removed == 1
    remaining = db_session.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.entity_id == job.id)
    ).all()
    assert remaining == []
