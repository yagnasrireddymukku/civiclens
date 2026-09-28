"""Request/response contract for /api/v1/eligibility — see docs/API.md
§18. `SourceSummary` is redefined locally rather than imported, matching
every other domain module's convention (see `app/documents/schemas.py`'s
docstring, CLAUDE.md rule 10).

`EligibilityAnswers` is the entire "submitted answers" surface (this
phase's §E): every field optional, range-validated, never persisted —
the route handler builds a plain dict and discards the Pydantic model
after conversion, it is never written to the database (this phase's §G).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.eligibility.enums import (
    ConditionStatus,
    EligibilityAttribute,
    EligibilityEntityType,
    EligibilityOperator,
    EligibilityOutcome,
)
from app.schemes.enums import EducationLevel
from app.sources.enums import VerificationStatus


class SourceSummary(BaseModel):
    organization: str
    title: str
    url: str


class EligibilityAnswers(BaseModel):
    """A citizen's submitted answers for one evaluation — stateless, not
    tied to any stored `Profile` (this phase's assessment: no auth module
    exists yet to attach a persisted profile to a request)."""

    model_config = ConfigDict(extra="forbid")

    age: int | None = Field(default=None, ge=0, le=130)
    income_annual: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    education_level: EducationLevel | None = None
    academic_percentage: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    academic_cgpa: Decimal | None = Field(default=None, ge=0, le=10, max_digits=4, decimal_places=2)
    # A `states.code` value (e.g. "AP"), not a UUID — the applicant's own
    # state of residence is something they can type/select directly; the
    # service layer never needs to resolve it to a `states.id` since rule
    # conditions store the same code, not a foreign key (see
    # `app/eligibility/models.py`'s module docstring).
    residence_state_code: str | None = Field(default=None, max_length=10)
    category: str | None = Field(default=None, max_length=100)


class EntitySummary(BaseModel):
    entity_type: EligibilityEntityType
    slug: str
    name: str


class CriterionQuestion(BaseModel):
    attribute: EligibilityAttribute
    operator: EligibilityOperator
    expected: str
    description: str | None


class CriteriaResponse(BaseModel):
    """`GET /eligibility/criteria` — the questions needed for an
    evaluation, with no answers submitted yet."""

    entity: EntitySummary
    supported: bool
    rule_id: uuid.UUID | None
    rule_version: int | None
    source: SourceSummary | None
    verification_status: VerificationStatus | None
    last_verified: datetime | None
    criteria: list[CriterionQuestion]


class ConditionResultSchema(BaseModel):
    attribute: EligibilityAttribute
    operator: EligibilityOperator
    description: str | None
    expected: str
    submitted_value: str | None
    status: ConditionStatus
    reason: str | None


class EvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: EligibilityEntityType
    entity_slug: str = Field(min_length=1, max_length=220)
    answers: EligibilityAnswers = Field(default_factory=EligibilityAnswers)


class EvaluateResponse(BaseModel):
    """`supported=False` means no verified, published eligibility rule
    exists for this entity yet — a distinct signal from the three
    `EligibilityOutcome` values, never fabricated as `INCOMPLETE` (this
    phase's kickoff: never declare eligibility without authoritative,
    structured, verified criteria). When `supported` is `True`, `outcome`
    and the rest of the evaluation trace are always populated."""

    entity: EntitySummary
    supported: bool
    message: str | None = None

    outcome: EligibilityOutcome | None = None
    conditions: list[ConditionResultSchema] = Field(default_factory=list)
    missing_attributes: list[EligibilityAttribute] = Field(default_factory=list)
    failed_attributes: list[EligibilityAttribute] = Field(default_factory=list)

    rule_id: uuid.UUID | None = None
    rule_version: int | None = None
    source: SourceSummary | None = None
    verification_status: VerificationStatus | None = None
    last_verified: datetime | None = None
    evaluated_at: datetime
