"""Orchestration tests for `app.ai.service.answer_question` — every
`GroundingStatus` branch, provider-unavailable degradation, and the
"a fabricated citation is rejected" property end to end (not just at
the `app.ai.citations` unit level).
"""

import asyncio

from sqlalchemy.orm import Session

from app.ai.enums import AIEntityType, GroundingStatus
from app.ai.indexing import index_one
from app.ai.service import answer_question
from app.jobs.service import sync_job_search_index
from tests.test_ai._helpers import FakeEmbeddingProvider, FakeLLMProvider
from tests.test_documents._helpers import make_organization, make_source, make_state
from tests.test_jobs._helpers import make_job


def _sync(coro):
    return asyncio.run(coro)


def _indexed_job(db_session: Session, embedding_provider, **overrides):
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source, **overrides)
    sync_job_search_index(db_session, job)
    _sync(
        index_one(
            db_session,
            entity_type=AIEntityType.JOB,
            entity_id=job.id,
            locale="en",
            embedding_provider=embedding_provider,
        )
    )
    return job


def test_answer_question_returns_provider_unavailable_when_no_llm_configured(
    db_session: Session,
) -> None:
    result = _sync(
        answer_question(
            db_session,
            question="What is the age limit for this job?",
            locale="en",
            entity_context_type=None,
            entity_context_slug=None,
            llm_provider=None,
            embedding_provider=None,
            max_tokens=512,
        )
    )
    assert result.grounding_status == GroundingStatus.PROVIDER_UNAVAILABLE
    assert result.answer is None


def test_answer_question_returns_insufficient_evidence_when_nothing_retrieved(
    db_session: Session,
) -> None:
    llm = FakeLLMProvider('{"answer": "x", "citation_ids": [1], "grounded": true}')

    result = _sync(
        answer_question(
            db_session,
            question="What is the age limit for a completely unrelated topic?",
            locale="en",
            entity_context_type=None,
            entity_context_slug=None,
            llm_provider=llm,
            embedding_provider=None,
            max_tokens=512,
        )
    )

    assert result.grounding_status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert result.answer is None
    assert llm.calls == []  # never called — cost control


def test_answer_question_returns_grounded_with_valid_citation(db_session: Session) -> None:
    embedding = FakeEmbeddingProvider(dimensions=8)
    job = _indexed_job(db_session, embedding, title="Test Junior Assistant Recruitment (Fixture)")
    llm = FakeLLMProvider(
        '{"answer": "The age limit is 18-35.", "citation_ids": [1], "grounded": true}'
    )

    result = _sync(
        answer_question(
            db_session,
            question="Junior Assistant Recruitment",
            locale="en",
            entity_context_type=None,
            entity_context_slug=None,
            llm_provider=llm,
            embedding_provider=embedding,
            max_tokens=512,
        )
    )

    assert result.grounding_status == GroundingStatus.GROUNDED
    assert result.answer == "The age limit is 18-35."
    assert len(result.citations) == 1
    assert result.citations[0].chunk.entity_id == job.id


def test_answer_question_returns_ungrounded_when_citation_is_fabricated(
    db_session: Session,
) -> None:
    embedding = FakeEmbeddingProvider(dimensions=8)
    _indexed_job(db_session, embedding, title="Test Junior Assistant Recruitment (Fixture)")
    # Only one evidence item is ever retrieved for this query, so
    # citation id 7 does not exist in the evidence set — simulating a
    # model trying to cite something outside what it was actually given.
    llm = FakeLLMProvider('{"answer": "Something.", "citation_ids": [7], "grounded": true}')

    result = _sync(
        answer_question(
            db_session,
            question="Junior Assistant Recruitment",
            locale="en",
            entity_context_type=None,
            entity_context_slug=None,
            llm_provider=llm,
            embedding_provider=embedding,
            max_tokens=512,
        )
    )

    assert result.grounding_status == GroundingStatus.UNGROUNDED
    assert result.answer is None
    assert result.citations == []


def test_answer_question_returns_ungrounded_for_unparseable_llm_output(
    db_session: Session,
) -> None:
    embedding = FakeEmbeddingProvider(dimensions=8)
    _indexed_job(db_session, embedding, title="Test Junior Assistant Recruitment (Fixture)")
    llm = FakeLLMProvider("I refuse to answer in JSON today.")

    result = _sync(
        answer_question(
            db_session,
            question="Junior Assistant Recruitment",
            locale="en",
            entity_context_type=None,
            entity_context_slug=None,
            llm_provider=llm,
            embedding_provider=embedding,
            max_tokens=512,
        )
    )

    assert result.grounding_status == GroundingStatus.UNGROUNDED
    assert result.answer is None


def test_answer_question_returns_provider_unavailable_on_llm_failure(db_session: Session) -> None:
    embedding = FakeEmbeddingProvider(dimensions=8)
    _indexed_job(db_session, embedding, title="Test Junior Assistant Recruitment (Fixture)")
    llm = FakeLLMProvider("irrelevant", raise_error=True)

    result = _sync(
        answer_question(
            db_session,
            question="Junior Assistant Recruitment",
            locale="en",
            entity_context_type=None,
            entity_context_slug=None,
            llm_provider=llm,
            embedding_provider=embedding,
            max_tokens=512,
        )
    )

    assert result.grounding_status == GroundingStatus.PROVIDER_UNAVAILABLE


def test_answer_question_degrades_to_lexical_only_when_embedding_provider_fails(
    db_session: Session,
) -> None:
    indexing_embedding = FakeEmbeddingProvider(dimensions=8)
    _indexed_job(
        db_session, indexing_embedding, title="Test Junior Assistant Recruitment (Fixture)"
    )
    failing_embedding = FakeEmbeddingProvider(dimensions=8, raise_error=True)
    llm = FakeLLMProvider('{"answer": "Ok.", "citation_ids": [1], "grounded": true}')

    result = _sync(
        answer_question(
            db_session,
            question="Junior Assistant Recruitment",
            locale="en",
            entity_context_type=None,
            entity_context_slug=None,
            llm_provider=llm,
            embedding_provider=failing_embedding,
            max_tokens=512,
        )
    )

    # Lexical retrieval still found it, so the request still succeeds
    # end to end even though the query-time embedding call failed.
    assert result.grounding_status == GroundingStatus.GROUNDED


def test_answer_question_includes_entity_context_chunk_even_without_text_match(
    db_session: Session,
) -> None:
    embedding = FakeEmbeddingProvider(dimensions=8)
    job = _indexed_job(db_session, embedding, title="Test Junior Assistant Recruitment (Fixture)")
    llm = FakeLLMProvider('{"answer": "Ok.", "citation_ids": [1], "grounded": true}')

    result = _sync(
        answer_question(
            db_session,
            question="What does this page say?",  # no lexical/semantic match at all
            locale="en",
            entity_context_type=AIEntityType.JOB,
            entity_context_slug=job.slug,
            llm_provider=llm,
            embedding_provider=None,
            max_tokens=512,
        )
    )

    assert result.grounding_status == GroundingStatus.GROUNDED
    assert result.citations[0].chunk.entity_id == job.id
