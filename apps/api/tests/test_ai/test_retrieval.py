"""Retrieval tests: lexical (reusing `search.service.search_documents`),
semantic (Python-side cosine similarity, filtered to the current
embedding model/dimensions), merge/de-dup, and — the most important
property here — the `search_documents` join as a trust gate: an
unpublished/expired entity is never retrievable even if its chunk row
still exists in `ai_knowledge_chunks`.
"""

import asyncio

from sqlalchemy.orm import Session

from app.ai.enums import AIEntityType, RetrievalMatchType
from app.ai.indexing import index_one
from app.ai.retrieval import (
    get_chunk_for_entity,
    lexical_retrieve,
    merge_retrieved,
    semantic_retrieve,
)
from app.jobs.enums import JobPublicationStatus
from app.jobs.service import sync_job_search_index
from tests.test_ai._helpers import FakeEmbeddingProvider, deterministic_fake_vector
from tests.test_documents._helpers import make_organization, make_source, make_state
from tests.test_jobs._helpers import make_job


def _sync(coro):
    return asyncio.run(coro)


def _indexed_job(
    db_session: Session,
    provider: FakeEmbeddingProvider,
    *,
    state=None,
    source=None,
    organization=None,
    **overrides,
):
    # `tests.test_documents._helpers.make_state`/`make_source` always
    # insert a fresh row (no get-or-create, unlike the fixtures.py
    # modules) — callers that need more than one indexed job in the same
    # test must create shared geography/source/organization once and
    # pass them in, rather than letting each call insert its own and
    # collide on the unique "ZZ" state code.
    state = state or make_state(db_session)
    source = source or make_source(db_session)
    organization = organization or make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source, **overrides)
    sync_job_search_index(db_session, job)
    _sync(
        index_one(
            db_session,
            entity_type=AIEntityType.JOB,
            entity_id=job.id,
            locale="en",
            embedding_provider=provider,
        )
    )
    return job


def test_lexical_retrieve_finds_an_indexed_job_by_title(db_session: Session) -> None:
    provider = FakeEmbeddingProvider(dimensions=8)
    job = _indexed_job(db_session, provider, title="Test Junior Assistant Recruitment (Fixture)")

    results = lexical_retrieve(db_session, query="Junior Assistant", locale="en", limit=5)

    assert len(results) == 1
    assert results[0].entity_id == job.id
    assert results[0].match_type == RetrievalMatchType.LEXICAL


def test_lexical_retrieve_returns_nothing_for_an_unindexed_but_searchable_job(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        title="Test Unindexed Job (Fixture)",
    )
    sync_job_search_index(db_session, job)  # searchable, but never RAG-indexed

    results = lexical_retrieve(db_session, query="Unindexed Job", locale="en", limit=5)

    assert results == []


def test_semantic_retrieve_ranks_by_cosine_similarity(db_session: Session) -> None:
    provider = FakeEmbeddingProvider(dimensions=8)
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job_a = _indexed_job(
        db_session,
        provider,
        state=state,
        source=source,
        organization=organization,
        title="Test Alpha Recruitment (Fixture)",
        summary="alpha alpha alpha",
    )
    job_b = _indexed_job(
        db_session,
        provider,
        state=state,
        source=source,
        organization=organization,
        title="Test Beta Recruitment (Fixture)",
        summary="beta beta beta",
    )

    query_vector = deterministic_fake_vector(
        "Test Alpha Recruitment (Fixture) alpha alpha alpha", provider.dimensions
    )
    results = semantic_retrieve(
        db_session,
        query_vector=query_vector,
        locale="en",
        embedding_model=provider.model,
        embedding_dimensions=provider.dimensions,
        limit=5,
    )

    assert results[0].entity_id == job_a.id
    assert any(r.entity_id == job_b.id for r in results)
    assert results[0].score >= results[1].score


def test_semantic_retrieve_filters_out_incompatible_embedding_model(db_session: Session) -> None:
    provider = FakeEmbeddingProvider(dimensions=8, model="fake-embed-1")
    _indexed_job(db_session, provider)

    query_vector = deterministic_fake_vector("anything", 8)
    results = semantic_retrieve(
        db_session,
        query_vector=query_vector,
        locale="en",
        embedding_model="a-different-model",
        embedding_dimensions=8,
        limit=5,
    )

    assert results == []


def test_search_documents_join_hides_unpublished_entity(db_session: Session) -> None:
    """The core trust-gate property: unpublishing an entity removes it
    from `search_documents`, which must make it invisible to both
    retrieval paths even though its `ai_knowledge_chunks` row is
    untouched."""

    provider = FakeEmbeddingProvider(dimensions=8)
    job = _indexed_job(db_session, provider, title="Test Soon Unpublished Job (Fixture)")

    job.publication_status = JobPublicationStatus.DRAFT
    db_session.flush()
    sync_job_search_index(db_session, job)  # removes it from search_documents

    lexical = lexical_retrieve(db_session, query="Soon Unpublished", locale="en", limit=5)
    semantic = semantic_retrieve(
        db_session,
        query_vector=deterministic_fake_vector("Soon Unpublished", 8),
        locale="en",
        embedding_model=provider.model,
        embedding_dimensions=provider.dimensions,
        limit=5,
    )
    direct = get_chunk_for_entity(db_session, entity_type="job", entity_id=job.id, locale="en")

    assert lexical == []
    assert all(r.entity_id != job.id for r in semantic)
    assert direct is None


def test_merge_retrieved_deduplicates_keeping_higher_score(db_session: Session) -> None:
    provider = FakeEmbeddingProvider(dimensions=8)
    job = _indexed_job(db_session, provider)

    lexical = lexical_retrieve(db_session, query=job.title, locale="en", limit=5)
    semantic = semantic_retrieve(
        db_session,
        query_vector=deterministic_fake_vector(job.title, 8),
        locale="en",
        embedding_model=provider.model,
        embedding_dimensions=provider.dimensions,
        limit=5,
    )

    merged = merge_retrieved(lexical, semantic, limit=5)

    matching = [r for r in merged if r.entity_id == job.id]
    assert len(matching) == 1


def test_get_chunk_for_entity_returns_the_chunk_directly(db_session: Session) -> None:
    provider = FakeEmbeddingProvider(dimensions=8)
    job = _indexed_job(db_session, provider)

    chunk = get_chunk_for_entity(db_session, entity_type="job", entity_id=job.id, locale="en")

    assert chunk is not None
    assert chunk.entity_id == job.id
