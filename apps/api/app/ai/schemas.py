"""Request/response contract for /api/v1/ai — see docs/API.md §19.
`SourceSummary` is redefined locally rather than imported, matching
every other domain module's convention (CLAUDE.md rule 10).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.ai.enums import AIEntityType, EligibilityExplanationStatus, GroundingStatus
from app.eligibility.enums import EligibilityEntityType, EligibilityOutcome
from app.eligibility.schemas import EligibilityAnswers
from app.sources.enums import VerificationStatus

MAX_QUESTION_LENGTH = 500
MIN_QUESTION_LENGTH = 3


class SourceSummary(BaseModel):
    organization: str
    title: str
    url: str


class EntityContext(BaseModel):
    """Optional hint that the citizen is asking while viewing a specific
    entity's page — see `app.ai.service.answer_question`."""

    model_config = ConfigDict(extra="forbid")

    entity_type: AIEntityType
    entity_slug: str = Field(min_length=1, max_length=220)


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=MIN_QUESTION_LENGTH, max_length=MAX_QUESTION_LENGTH)
    locale: str = Field(default="en", pattern="^(en|te)$")
    entity_context: EntityContext | None = None


class CitationSchema(BaseModel):
    citation_id: int
    title: str
    route: str
    source: SourceSummary
    verification_status: VerificationStatus
    last_verified: datetime | None
    needs_review_caveat: bool


class AskResponse(BaseModel):
    """`answer` is `null` for every `grounding_status` except
    `GROUNDED` — an ungrounded or unavailable answer is never shown as
    if it were a real one (docs/AI_ARCHITECTURE.md §6)."""

    grounding_status: GroundingStatus
    answer: str | None
    citations: list[CitationSchema] = Field(default_factory=list)
    message: str
    disclaimer: str
    locale: str


class ExplainEligibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: EligibilityEntityType
    entity_slug: str = Field(min_length=1, max_length=220)
    answers: EligibilityAnswers = Field(default_factory=EligibilityAnswers)
    locale: str = Field(default="en", pattern="^(en|te)$")


class ExplainEligibilityResponse(BaseModel):
    status: EligibilityExplanationStatus
    outcome: EligibilityOutcome | None
    explanation: str | None
    rule_id: uuid.UUID | None
    rule_version: int | None
    source: SourceSummary | None
    verification_status: VerificationStatus | None
    last_verified: datetime | None
    message: str


class ProviderHealth(BaseModel):
    llm_configured: bool
    llm_provider: str
    embedding_configured: bool
    embedding_provider: str
