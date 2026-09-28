"""GET /api/v1/eligibility/criteria, POST /api/v1/eligibility/evaluate —
see docs/API.md §18 and docs/ELIGIBILITY_ENGINE.md. Route handlers only
translate between HTTP and `app.eligibility.service`/`.evaluator` — no
query or evaluation logic lives in this file, mirroring every other
domain router.

Submitted answers are read, evaluated, and discarded within this request
— never persisted to the database, never written to an application log
(no request-body logging exists anywhere in `app/core/logging.py`, and
this router adds none) — this phase's §G.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.eligibility import service
from app.eligibility.enums import ConditionStatus, EligibilityEntityType
from app.eligibility.evaluator import ConditionResult, expected_display
from app.eligibility.schemas import (
    ConditionResultSchema,
    CriteriaResponse,
    CriterionQuestion,
    EntitySummary,
    EvaluateRequest,
    EvaluateResponse,
    SourceSummary,
)

router = APIRouter(prefix="/eligibility", tags=["eligibility"])


def _condition_schema(result: ConditionResult) -> ConditionResultSchema:
    return ConditionResultSchema(
        attribute=result.attribute,
        operator=result.operator,
        description=result.description,
        expected=result.expected,
        submitted_value=result.submitted_value,
        status=result.status,
        reason=result.reason,
    )


@router.get("/criteria", response_model=CriteriaResponse)
def get_criteria(
    entity_type: EligibilityEntityType = Query(...),
    entity_slug: str = Query(..., min_length=1, max_length=220),
    db: Session = Depends(get_db),
) -> CriteriaResponse:
    entity = service.resolve_entity(db, entity_type, entity_slug)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity_summary = EntitySummary(
        entity_type=entity.entity_type, slug=entity.slug, name=entity.name
    )
    row = service.get_evaluable_rule(db, entity_type, entity.entity_id)
    if row is None:
        return CriteriaResponse(
            entity=entity_summary,
            supported=False,
            rule_id=None,
            rule_version=None,
            source=None,
            verification_status=None,
            last_verified=None,
            criteria=[],
        )

    spec = service.build_rule_spec(row.rule)
    return CriteriaResponse(
        entity=entity_summary,
        supported=True,
        rule_id=row.rule.id,
        rule_version=row.rule.rule_version,
        source=SourceSummary(
            organization=row.source.organization, title=row.source.title, url=row.source.url
        ),
        verification_status=row.rule.verification_status,
        last_verified=row.rule.last_verified_at,
        criteria=[
            CriterionQuestion(
                attribute=condition.attribute,
                operator=condition.operator,
                expected=expected_display(condition),
                description=condition.description,
            )
            for condition in spec.conditions
        ],
    )


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(payload: EvaluateRequest, db: Session = Depends(get_db)) -> EvaluateResponse:
    entity = service.resolve_entity(db, payload.entity_type, payload.entity_slug)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity_summary = EntitySummary(
        entity_type=entity.entity_type, slug=entity.slug, name=entity.name
    )
    row = service.get_evaluable_rule(db, payload.entity_type, entity.entity_id)
    if row is None:
        return EvaluateResponse(
            entity=entity_summary,
            supported=False,
            message=(
                "No verified eligibility criteria are available for this "
                f"{payload.entity_type.value.lower()} yet."
            ),
            evaluated_at=datetime.now(UTC),
        )

    result, evaluated_at = service.run_evaluation(row.rule, payload.answers)
    conditions = [_condition_schema(c) for c in result.conditions]
    return EvaluateResponse(
        entity=entity_summary,
        supported=True,
        outcome=result.outcome,
        conditions=conditions,
        missing_attributes=[
            c.attribute for c in result.conditions if c.status == ConditionStatus.UNKNOWN
        ],
        failed_attributes=[
            c.attribute for c in result.conditions if c.status == ConditionStatus.FAIL
        ],
        rule_id=row.rule.id,
        rule_version=row.rule.rule_version,
        source=SourceSummary(
            organization=row.source.organization, title=row.source.title, url=row.source.url
        ),
        verification_status=row.rule.verification_status,
        last_verified=row.rule.last_verified_at,
        evaluated_at=evaluated_at,
    )
