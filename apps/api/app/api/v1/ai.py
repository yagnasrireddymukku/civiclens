"""POST /api/v1/ai/ask, POST /api/v1/ai/explain-eligibility,
GET /api/v1/ai/health — see docs/API.md §19. Route handlers only
translate between HTTP and `app.ai.service`/`.eligibility_explainer` —
no retrieval/prompting/citation logic lives in this file.

Deliberately no re-indexing route exists here or anywhere else — no
auth/role-check mechanism exists anywhere in this codebase yet (verified
by hand), so per this phase's explicit "never expose an unauthenticated
destructive indexing endpoint," re-indexing is exposed only as an
internal service function (`app.ai.indexing.reindex_all`) and a manual
ops script (`scripts/reindex_ai_knowledge.py`).

Submitted questions and eligibility answers are read, evaluated, and
discarded within the request — never persisted, never logged (no
request-body logging exists anywhere in `app/core/logging.py`, and this
router adds none) — this phase's explicit privacy requirement.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai import eligibility_explainer, service
from app.ai.providers import get_embedding_provider, get_llm_provider
from app.ai.rate_limit import enforce_ai_rate_limit
from app.ai.schemas import (
    AskRequest,
    AskResponse,
    CitationSchema,
    ExplainEligibilityRequest,
    ExplainEligibilityResponse,
    ProviderHealth,
    SourceSummary,
)
from app.ai.service import DISCLAIMER
from app.core.config import get_settings
from app.core.db.session import get_db

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ask", response_model=AskResponse, dependencies=[Depends(enforce_ai_rate_limit)])
async def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    settings = get_settings()
    result = await service.answer_question(
        db,
        question=payload.question,
        locale=payload.locale,
        entity_context_type=payload.entity_context.entity_type if payload.entity_context else None,
        entity_context_slug=payload.entity_context.entity_slug if payload.entity_context else None,
        llm_provider=get_llm_provider(),
        embedding_provider=get_embedding_provider(),
        max_tokens=settings.ai_llm_max_tokens,
    )
    return AskResponse(
        grounding_status=result.grounding_status,
        answer=result.answer,
        citations=[
            CitationSchema(
                citation_id=c.citation_id,
                title=c.chunk.title,
                route=c.chunk.route,
                source=SourceSummary(
                    organization=c.chunk.source_organization,
                    title=c.chunk.source_title,
                    url=c.chunk.source_url,
                ),
                verification_status=c.chunk.verification_status,
                last_verified=c.chunk.last_verified_at,
                needs_review_caveat=c.chunk.needs_review_caveat,
            )
            for c in result.citations
        ],
        message=result.message,
        disclaimer=DISCLAIMER,
        locale=payload.locale,
    )


@router.post(
    "/explain-eligibility",
    response_model=ExplainEligibilityResponse,
    dependencies=[Depends(enforce_ai_rate_limit)],
)
async def explain_eligibility(
    payload: ExplainEligibilityRequest, db: Session = Depends(get_db)
) -> ExplainEligibilityResponse:
    result = await eligibility_explainer.explain_eligibility(
        db,
        entity_type=payload.entity_type,
        entity_slug=payload.entity_slug,
        answers=payload.answers,
        llm_provider=get_llm_provider(),
    )
    source = (
        SourceSummary(
            organization=result.source_organization or "",
            title=result.source_title or "",
            url=result.source_url or "",
        )
        if result.source_organization is not None
        else None
    )
    return ExplainEligibilityResponse(
        status=result.status,
        outcome=result.outcome,
        explanation=result.explanation,
        rule_id=result.rule_id,
        rule_version=result.rule_version,
        source=source,
        verification_status=result.verification_status,
        last_verified=result.last_verified_at,
        message=result.message,
    )


@router.get("/health", response_model=ProviderHealth)
def ai_health() -> ProviderHealth:
    settings = get_settings()
    return ProviderHealth(
        llm_configured=get_llm_provider() is not None,
        llm_provider=settings.ai_llm_provider,
        embedding_configured=get_embedding_provider() is not None,
        embedding_provider=settings.ai_embedding_provider,
    )
