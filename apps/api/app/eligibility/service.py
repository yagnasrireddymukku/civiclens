"""Eligibility domain query/business logic — resolves a `(entity_type,
entity_slug)` pair to the one evaluable `EligibilityRule`, converts it to
the pure `app.eligibility.evaluator` dataclasses, and converts submitted
`EligibilityAnswers` into the plain mapping the evaluator accepts. No
answer is ever written to the database (this phase's §G) — this module
only reads.

Entity resolution deliberately reuses each domain's own `get_*_by_slug`
(which already applies that domain's visibility rule) rather than
querying `jobs`/`schemes`/`services` directly — the same cross-module-read
pattern `app.documents.service.get_required_by` established in Phase 10,
justified by CLAUDE.md rule 10's own carve-out for an explicit, modeled
relationship.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.eligibility.enums import EligibilityAttribute, EligibilityEntityType
from app.eligibility.enums import EligibilityRulePublicationStatus as RulePublicationStatus
from app.eligibility.evaluator import (
    AnswerValue,
    ConditionSpec,
    EvaluationResult,
    RuleSpec,
    evaluate_rule,
)
from app.eligibility.models import EligibilityRule
from app.eligibility.schemas import EligibilityAnswers
from app.jobs import service as jobs_service
from app.schemes import service as schemes_service
from app.services import service as services_service
from app.sources.enums import VerificationStatus
from app.sources.models import Source

_ENTITY_COLUMN = {
    EligibilityEntityType.JOB: EligibilityRule.job_id,
    EligibilityEntityType.SCHEME: EligibilityRule.scheme_id,
    EligibilityEntityType.SERVICE: EligibilityRule.service_id,
}


@dataclass(frozen=True, slots=True)
class ResolvedEntity:
    entity_type: EligibilityEntityType
    entity_id: uuid.UUID
    slug: str
    name: str


def resolve_entity(
    session: Session, entity_type: EligibilityEntityType, slug: str
) -> ResolvedEntity | None:
    """`None` for an entity that doesn't exist *or* isn't publicly
    visible — identical "don't distinguish the two" convention every
    other domain's `get_*_by_slug` already follows."""

    if entity_type == EligibilityEntityType.JOB:
        job_row = jobs_service.get_job_by_slug(session, slug)
        if job_row is None:
            return None
        return ResolvedEntity(entity_type, job_row.job.id, slug, job_row.job.title)
    if entity_type == EligibilityEntityType.SCHEME:
        scheme_row = schemes_service.get_scheme_by_slug(session, slug)
        if scheme_row is None:
            return None
        return ResolvedEntity(entity_type, scheme_row.scheme.id, slug, scheme_row.scheme.name)
    if entity_type == EligibilityEntityType.SERVICE:
        service_row = services_service.get_service_by_slug(session, slug)
        if service_row is None:
            return None
        return ResolvedEntity(entity_type, service_row.service.id, slug, service_row.service.name)
    raise AssertionError(f"unreachable entity_type {entity_type}")  # pragma: no cover


def _evaluable_predicate() -> Any:
    return and_(
        EligibilityRule.publication_status == RulePublicationStatus.PUBLISHED,
        # Stricter than the standard display-visibility rule (VERIFIED OR
        # NEEDS_REVIEW): an evaluation is a claim of fact, so only a fully
        # `VERIFIED` rule may ever produce ELIGIBLE/NOT_ELIGIBLE/
        # INCOMPLETE — see module docstring in `app/eligibility/models.py`.
        EligibilityRule.verification_status == VerificationStatus.VERIFIED,
        EligibilityRule.deleted_at.is_(None),
    )


@dataclass(frozen=True, slots=True)
class RuleRow:
    rule: EligibilityRule
    source: Source


def get_evaluable_rule(
    session: Session, entity_type: EligibilityEntityType, entity_id: uuid.UUID
) -> RuleRow | None:
    column = _ENTITY_COLUMN[entity_type]
    stmt = (
        select(EligibilityRule, Source)
        .join(Source, EligibilityRule.source_id == Source.id)
        .options(selectinload(EligibilityRule.conditions))
        .where(column == entity_id, _evaluable_predicate())
        .order_by(EligibilityRule.rule_version.desc())
        .limit(1)
    )
    result = session.execute(stmt).first()
    if result is None:
        return None
    rule, source = result
    if not rule.conditions:
        # A published, verified rule with zero conditions can't express
        # anything — never treated as trivially evaluable (this phase's
        # §D: never a silent authoritative outcome from inadequate data).
        return None
    return RuleRow(rule=rule, source=source)


def build_rule_spec(rule: EligibilityRule) -> RuleSpec:
    return RuleSpec(
        rule_id=rule.id,
        rule_version=rule.rule_version,
        conditions=tuple(
            ConditionSpec(
                condition_id=condition.id,
                attribute=condition.attribute,
                operator=condition.operator,
                description=condition.description,
                numeric_value=condition.numeric_value,
                numeric_value_max=condition.numeric_value_max,
                text_value=condition.text_value,
                text_values=tuple(condition.text_values) if condition.text_values else None,
            )
            for condition in rule.conditions
        ),
    )


_ANSWER_FIELDS: dict[EligibilityAttribute, str] = {
    EligibilityAttribute.AGE: "age",
    EligibilityAttribute.INCOME_ANNUAL: "income_annual",
    EligibilityAttribute.EDUCATION_LEVEL: "education_level",
    EligibilityAttribute.ACADEMIC_PERCENTAGE: "academic_percentage",
    EligibilityAttribute.ACADEMIC_CGPA: "academic_cgpa",
    EligibilityAttribute.RESIDENCE_STATE: "residence_state_code",
    EligibilityAttribute.CATEGORY: "category",
}


def build_answer_map(answers: EligibilityAnswers) -> dict[EligibilityAttribute, AnswerValue]:
    """Converts the validated request model into the plain mapping the
    pure evaluator accepts — an enum member (`education_level`) becomes
    its `.value` string, everything else passes through as-is."""

    result: dict[EligibilityAttribute, AnswerValue] = {}
    for attribute, field_name in _ANSWER_FIELDS.items():
        value = getattr(answers, field_name)
        if value is None:
            continue
        result[attribute] = value.value if hasattr(value, "value") else value
    return result


def run_evaluation(
    rule: EligibilityRule, answers: EligibilityAnswers
) -> tuple[EvaluationResult, datetime]:
    spec = build_rule_spec(rule)
    answer_map = build_answer_map(answers)
    return evaluate_rule(spec, answer_map), datetime.now(UTC)
