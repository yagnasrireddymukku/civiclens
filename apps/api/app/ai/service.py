"""Civic AI orchestration — the one place `retrieval`, `prompting`,
`citations`, and a provider call are wired together for the general
question-answering path (docs/AI_ARCHITECTURE.md §1). Route handlers
(`app/api/v1/ai.py`) only translate HTTP <-> this module.

Cost control (this phase's explicit requirement): the LLM is never
called when retrieval returns nothing (`INSUFFICIENT_EVIDENCE`) — there
is nothing it could ground an answer in anyway.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai import entity_resolution, prompting, retrieval
from app.ai.citations import ValidatedCitation, parse_llm_response, validate_citations
from app.ai.enums import AIEntityType, GroundingStatus
from app.ai.providers import (
    EmbeddingProvider,
    EmbeddingProviderError,
    LLMProvider,
    LLMProviderError,
)

DISCLAIMER = (
    "This is an AI-generated explanation based on CivicLens's published information. "
    "It is informational only, not an official government decision, and does not replace "
    "advice from the relevant government authority."
)

_RETRIEVAL_LIMIT = 6


@dataclass(frozen=True, slots=True)
class AIAnswer:
    grounding_status: GroundingStatus
    answer: str | None
    citations: list[ValidatedCitation]
    message: str


async def answer_question(
    session: Session,
    *,
    question: str,
    locale: str,
    entity_context_type: AIEntityType | None,
    entity_context_slug: str | None,
    llm_provider: LLMProvider | None,
    embedding_provider: EmbeddingProvider | None,
    max_tokens: int,
) -> AIAnswer:
    if llm_provider is None:
        return AIAnswer(
            grounding_status=GroundingStatus.PROVIDER_UNAVAILABLE,
            answer=None,
            citations=[],
            message=(
                "Civic AI is not currently available. You can still use CivicLens search "
                "and browse published jobs, services, schemes, and documents directly."
            ),
        )

    lexical = retrieval.lexical_retrieve(
        session, query=question, locale=locale, limit=_RETRIEVAL_LIMIT
    )

    semantic: list[retrieval.RetrievedChunk] = []
    if embedding_provider is not None:
        try:
            embed_result = await embedding_provider.embed([question])
        except EmbeddingProviderError:
            semantic = []  # degrade to lexical-only, not a request failure
        else:
            (query_vector,) = embed_result.vectors
            semantic = retrieval.semantic_retrieve(
                session,
                query_vector=query_vector,
                locale=locale,
                embedding_model=embedding_provider.model,
                embedding_dimensions=embedding_provider.dimensions,
                limit=_RETRIEVAL_LIMIT,
            )

    merged = retrieval.merge_retrieved(lexical, semantic, limit=_RETRIEVAL_LIMIT)

    if entity_context_type is not None and entity_context_slug is not None:
        resolved = entity_resolution.resolve_entity(
            session, entity_context_type, entity_context_slug
        )
        if resolved is not None:
            context_chunk = retrieval.get_chunk_for_entity(
                session,
                entity_type=resolved.entity_type.value,
                entity_id=resolved.entity_id,
                locale=locale,
            )
            if context_chunk is not None:
                merged = retrieval.merge_retrieved([context_chunk], merged, limit=_RETRIEVAL_LIMIT)

    if not merged:
        return AIAnswer(
            grounding_status=GroundingStatus.INSUFFICIENT_EVIDENCE,
            answer=None,
            citations=[],
            message=(
                "CivicLens does not have enough published information to answer this yet. "
                "Try CivicLens search for related results."
            ),
        )

    evidence_block = prompting.build_evidence_block(merged)
    user_prompt = prompting.build_user_prompt(question=question, evidence_block=evidence_block)

    try:
        completion = await llm_provider.complete(
            system_prompt=prompting.SYSTEM_PROMPT, user_prompt=user_prompt, max_tokens=max_tokens
        )
    except LLMProviderError:
        return AIAnswer(
            grounding_status=GroundingStatus.PROVIDER_UNAVAILABLE,
            answer=None,
            citations=[],
            message=(
                "Civic AI is temporarily unavailable. You can still use CivicLens search "
                "and browse published information directly."
            ),
        )

    parsed = parse_llm_response(completion.text)
    if parsed is None:
        return AIAnswer(
            grounding_status=GroundingStatus.UNGROUNDED,
            answer=None,
            citations=[],
            message="CivicLens could not produce a reliably grounded answer to this question.",
        )

    validated = validate_citations(parsed, merged)
    if not validated:
        return AIAnswer(
            grounding_status=GroundingStatus.UNGROUNDED,
            answer=None,
            citations=[],
            message="CivicLens could not find a reliably sourced answer to this question.",
        )

    return AIAnswer(
        grounding_status=GroundingStatus.GROUNDED,
        answer=parsed.answer,
        citations=validated,
        message="",
    )
