"""Explains a deterministic Eligibility Engine result in plain language
— never computes one. This module calls `app.eligibility.service`'s
actual public functions unmodified (`resolve_entity`,
`get_evaluable_rule`, `run_evaluation`) — the exact same code path
`app/api/v1/eligibility.py` uses — and only ever *phrases* the result
that comes back.

**The safety property this module exists to guarantee**: no matter what
the LLM returns, the outcome shown to the user is always
`EvaluationResult.outcome` from the real engine. If the LLM's own
self-reported `stated_outcome` doesn't match that exactly, its phrasing
is discarded entirely and a template-based explanation (built directly
from the evaluation trace, no LLM involved) is used instead. This is
tested directly in `tests/test_ai/test_eligibility_explainer.py` with a
fake provider that always tries to state the wrong outcome.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.ai.enums import EligibilityExplanationStatus
from app.ai.providers import LLMProvider, LLMProviderError
from app.eligibility import service as eligibility_service
from app.eligibility.enums import ConditionStatus, EligibilityEntityType, EligibilityOutcome
from app.eligibility.evaluator import EvaluationResult
from app.eligibility.schemas import EligibilityAnswers
from app.sources.enums import VerificationStatus

ELIGIBILITY_EXPLAIN_SYSTEM_PROMPT = """You are the CivicLens Civic AI assistant, explaining a \
result already decided by CivicLens's own deterministic Eligibility Engine. You do not \
compute eligibility yourself. You are given the exact outcome and a criterion-by-criterion \
trace the engine already produced, and your only job is to explain it clearly in plain \
language.

Rules:
1. The outcome given to you (ELIGIBLE, NOT_ELIGIBLE, or INCOMPLETE) is final and already \
decided elsewhere. You must restate exactly that outcome in "stated_outcome" — never a \
different one, never a qualified or softened version of it, never a guess of your own.
2. Explain why each given criterion passed, failed, or could not be assessed due to missing \
information, using only the criteria given to you below. Never invent a criterion, age \
limit, income ceiling, deadline, or document requirement not present in the given trace.
3. If a criterion failed or is missing information, state that plainly — never hide or \
soften it.
4. State plainly that this is an informational explanation of a CivicLens check, not an \
official government determination.
5. Respond only in the language of the request (English or Telugu).

Respond with exactly one JSON object, no other text before or after it:
{"explanation": "<plain-language explanation>", \
"stated_outcome": "ELIGIBLE" | "NOT_ELIGIBLE" | "INCOMPLETE"}
"""


def _template_explanation(result: EvaluationResult) -> str:
    lines = []
    for condition in result.conditions:
        if condition.status == ConditionStatus.PASS:
            lines.append(f"Met: {condition.description or condition.attribute.value}.")
        elif condition.status == ConditionStatus.FAIL:
            lines.append(
                f"Not met: {condition.description or condition.attribute.value} "
                f"(required {condition.expected}, submitted {condition.submitted_value})."
            )
        else:
            lines.append(
                f"Could not be assessed: {condition.description or condition.attribute.value} "
                "— no answer was provided for this."
            )
    return " ".join(lines)


def _build_trace_prompt(result: EvaluationResult) -> str:
    trace = [
        {
            "attribute": c.attribute.value,
            "status": c.status.value,
            "expected": c.expected,
            "submitted_value": c.submitted_value,
            "description": c.description,
        }
        for c in result.conditions
    ]
    return f"Decided outcome: {result.outcome.value}\nCriterion trace (JSON): {json.dumps(trace)}"


def _parse_stated_outcome(raw_text: str) -> tuple[str | None, str | None]:
    """Returns `(explanation, stated_outcome)`, either of which may be
    `None` on any parse/shape failure — callers treat that identically
    to a mismatched outcome (discard, use the template fallback)."""

    text = raw_text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None, None
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    explanation = payload.get("explanation")
    stated_outcome = payload.get("stated_outcome")
    if not isinstance(explanation, str) or not isinstance(stated_outcome, str):
        return None, None
    return explanation, stated_outcome


@dataclass(frozen=True, slots=True)
class EligibilityExplanation:
    status: EligibilityExplanationStatus
    outcome: EligibilityOutcome | None
    explanation: str | None
    rule_id: uuid.UUID | None
    rule_version: int | None
    source_organization: str | None
    source_title: str | None
    source_url: str | None
    verification_status: VerificationStatus | None
    last_verified_at: datetime | None
    message: str


async def explain_eligibility(
    session: Session,
    *,
    entity_type: EligibilityEntityType,
    entity_slug: str,
    answers: EligibilityAnswers,
    llm_provider: LLMProvider | None,
) -> EligibilityExplanation:
    entity = eligibility_service.resolve_entity(session, entity_type, entity_slug)
    if entity is None:
        return EligibilityExplanation(
            status=EligibilityExplanationStatus.ENTITY_NOT_FOUND,
            outcome=None,
            explanation=None,
            rule_id=None,
            rule_version=None,
            source_organization=None,
            source_title=None,
            source_url=None,
            verification_status=None,
            last_verified_at=None,
            message="No such entity was found, or it is not currently published.",
        )

    row = eligibility_service.get_evaluable_rule(session, entity_type, entity.entity_id)
    if row is None:
        return EligibilityExplanation(
            status=EligibilityExplanationStatus.NOT_SUPPORTED,
            outcome=None,
            explanation=None,
            rule_id=None,
            rule_version=None,
            source_organization=None,
            source_title=None,
            source_url=None,
            verification_status=None,
            last_verified_at=None,
            message=(
                "Eligibility cannot currently be determined by CivicLens for this "
                f"{entity_type.value.lower()} — no verified, published eligibility "
                "criteria are available yet."
            ),
        )

    result, _evaluated_at = eligibility_service.run_evaluation(row.rule, answers)

    explanation = _template_explanation(result)
    if llm_provider is not None:
        try:
            completion = await llm_provider.complete(
                system_prompt=ELIGIBILITY_EXPLAIN_SYSTEM_PROMPT,
                user_prompt=_build_trace_prompt(result),
                max_tokens=512,
            )
        except LLMProviderError:
            # Graceful degradation, not a request failure — the
            # template explanation (built straight from the real trace)
            # is always a safe, correct fallback.
            pass
        else:
            llm_explanation, stated_outcome = _parse_stated_outcome(completion.text)
            if llm_explanation is not None and stated_outcome == result.outcome.value:
                explanation = llm_explanation
            # A mismatched or unparseable `stated_outcome` means the
            # LLM's phrasing is discarded entirely — never shown, even
            # partially — per this module's safety property.

    return EligibilityExplanation(
        status=EligibilityExplanationStatus.EXPLAINED,
        outcome=result.outcome,
        explanation=explanation,
        rule_id=row.rule.id,
        rule_version=row.rule.rule_version,
        source_organization=row.source.organization,
        source_title=row.source.title,
        source_url=row.source.url,
        verification_status=row.rule.verification_status,
        last_verified_at=row.rule.last_verified_at,
        message="",
    )
