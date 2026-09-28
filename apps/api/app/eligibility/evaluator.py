"""The deterministic evaluation core — docs/ELIGIBILITY_ENGINE.md §2-4.

Pure functions only: no database session, no HTTP, no LLM call, no wall-
clock read. Every value that could vary between calls (the rule, the
answers) is passed in explicitly, so `evaluate_rule` is trivially
reproducible for the same `(rule, answers)` pair — the reproducibility
docs/DATA_GOVERNANCE.md and this phase's kickoff ask for, satisfied by
construction rather than by a caching layer.

`app.eligibility.service` is the only caller in production code; it is
responsible for loading `EligibilityRule`/`EligibilityCondition` ORM rows,
converting them to the `RuleSpec`/`ConditionSpec` dataclasses below, and
converting a validated `EligibilityAnswers` Pydantic model into the plain
`Mapping[EligibilityAttribute, AnswerValue]` this module accepts. Nothing
here imports SQLAlchemy or Pydantic.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.eligibility.enums import (
    ConditionStatus,
    EligibilityAttribute,
    EligibilityOperator,
    EligibilityOutcome,
)

# Every numeric answer/condition value is coerced to Decimal before
# comparison — never float — so a threshold like 60.00 never drifts to
# 59.999999999999 (this phase's §B).
AnswerValue = Decimal | str | None

NUMERIC_ATTRIBUTES = frozenset(
    {
        EligibilityAttribute.AGE,
        EligibilityAttribute.INCOME_ANNUAL,
        EligibilityAttribute.ACADEMIC_PERCENTAGE,
        EligibilityAttribute.ACADEMIC_CGPA,
    }
)
TEXT_ATTRIBUTES = frozenset(
    {
        EligibilityAttribute.EDUCATION_LEVEL,
        EligibilityAttribute.RESIDENCE_STATE,
        EligibilityAttribute.CATEGORY,
    }
)

NUMERIC_OPERATORS = frozenset(
    {
        EligibilityOperator.EQ,
        EligibilityOperator.NEQ,
        EligibilityOperator.GTE,
        EligibilityOperator.LTE,
        EligibilityOperator.BETWEEN,
    }
)
TEXT_OPERATORS = frozenset(
    {
        EligibilityOperator.EQ,
        EligibilityOperator.NEQ,
        EligibilityOperator.IN,
        EligibilityOperator.NOT_IN,
    }
)


class InvalidEligibilityRuleError(ValueError):
    """Raised when a condition's attribute/operator/value combination is
    malformed, unsupported, or internally contradictory — never silently
    coerced into something evaluable (this phase's §B: "reject malformed,
    unsupported, contradictory or untrusted rules safely")."""


@dataclass(frozen=True, slots=True)
class ConditionSpec:
    condition_id: uuid.UUID
    attribute: EligibilityAttribute
    operator: EligibilityOperator
    description: str | None
    numeric_value: Decimal | None = None
    numeric_value_max: Decimal | None = None
    text_value: str | None = None
    text_values: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        validate_condition_shape(self)


@dataclass(frozen=True, slots=True)
class RuleSpec:
    rule_id: uuid.UUID
    rule_version: int
    conditions: tuple[ConditionSpec, ...]


@dataclass(frozen=True, slots=True)
class ConditionResult:
    condition_id: uuid.UUID
    attribute: EligibilityAttribute
    operator: EligibilityOperator
    description: str | None
    expected: str
    submitted_value: str | None
    status: ConditionStatus
    reason: str | None


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    outcome: EligibilityOutcome
    conditions: tuple[ConditionResult, ...]


def validate_condition_shape(condition: ConditionSpec) -> None:
    """Rejects a condition whose attribute/operator/value shape could
    never be evaluated safely — called both when building a `ConditionSpec`
    from a database row and when a fixture/future rule-authoring path
    constructs one, so a malformed rule can never reach `evaluate_rule`."""

    attribute, operator = condition.attribute, condition.operator

    if attribute in NUMERIC_ATTRIBUTES:
        if operator not in NUMERIC_OPERATORS:
            raise InvalidEligibilityRuleError(
                f"Operator {operator} is not supported for numeric attribute {attribute}."
            )
        if operator == EligibilityOperator.BETWEEN:
            if condition.numeric_value is None or condition.numeric_value_max is None:
                raise InvalidEligibilityRuleError(
                    "BETWEEN requires both numeric_value and numeric_value_max."
                )
            if condition.numeric_value > condition.numeric_value_max:
                raise InvalidEligibilityRuleError(
                    "BETWEEN's lower bound must not exceed its upper bound."
                )
        elif condition.numeric_value is None:
            raise InvalidEligibilityRuleError(f"{operator} requires numeric_value.")
    elif attribute in TEXT_ATTRIBUTES:
        if operator not in TEXT_OPERATORS:
            raise InvalidEligibilityRuleError(
                f"Operator {operator} is not supported for text attribute {attribute}."
            )
        if operator in (EligibilityOperator.IN, EligibilityOperator.NOT_IN):
            if not condition.text_values:
                raise InvalidEligibilityRuleError(f"{operator} requires a non-empty text_values.")
        elif not condition.text_value:
            raise InvalidEligibilityRuleError(f"{operator} requires text_value.")
    else:  # pragma: no cover - EligibilityAttribute is exhaustively partitioned above
        raise InvalidEligibilityRuleError(f"Unrecognized attribute {attribute}.")


def _coerce_numeric_answer(value: Decimal | str) -> Decimal:
    # Only ever called with a non-`None` answer — `_evaluate_condition`
    # handles the missing-answer (`UNKNOWN`) case before reaching here.
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:  # pragma: no cover - upstream Pydantic validation catches this
        raise InvalidEligibilityRuleError(f"Answer {value!r} is not a valid number.") from exc


def expected_display(condition: ConditionSpec) -> str:
    op = condition.operator
    if op == EligibilityOperator.BETWEEN:
        return f"between {condition.numeric_value} and {condition.numeric_value_max} (inclusive)"
    if op == EligibilityOperator.GTE:
        return f">= {condition.numeric_value}"
    if op == EligibilityOperator.LTE:
        return f"<= {condition.numeric_value}"
    if op in (EligibilityOperator.EQ, EligibilityOperator.NEQ):
        symbol = "=" if op == EligibilityOperator.EQ else "!="
        value = (
            condition.numeric_value if condition.numeric_value is not None else condition.text_value
        )
        return f"{symbol} {value}"
    if op in (EligibilityOperator.IN, EligibilityOperator.NOT_IN):
        joined = ", ".join(condition.text_values or ())
        prefix = "one of" if op == EligibilityOperator.IN else "none of"
        return f"{prefix}: {joined}"
    raise AssertionError(f"unreachable operator {op}")  # pragma: no cover


def _evaluate_condition(condition: ConditionSpec, answer: AnswerValue) -> ConditionResult:
    if answer is None:
        return ConditionResult(
            condition_id=condition.condition_id,
            attribute=condition.attribute,
            operator=condition.operator,
            description=condition.description,
            expected=expected_display(condition),
            submitted_value=None,
            status=ConditionStatus.UNKNOWN,
            reason="No answer was provided for this attribute.",
        )

    op = condition.operator
    passed: bool
    if condition.attribute in NUMERIC_ATTRIBUTES:
        numeric_answer = _coerce_numeric_answer(answer)
        if op == EligibilityOperator.BETWEEN:
            assert condition.numeric_value is not None and condition.numeric_value_max is not None
            passed = condition.numeric_value <= numeric_answer <= condition.numeric_value_max
        elif op == EligibilityOperator.GTE:
            assert condition.numeric_value is not None
            passed = numeric_answer >= condition.numeric_value
        elif op == EligibilityOperator.LTE:
            assert condition.numeric_value is not None
            passed = numeric_answer <= condition.numeric_value
        elif op == EligibilityOperator.EQ:
            assert condition.numeric_value is not None
            passed = numeric_answer == condition.numeric_value
        elif op == EligibilityOperator.NEQ:
            assert condition.numeric_value is not None
            passed = numeric_answer != condition.numeric_value
        else:  # pragma: no cover - validate_condition_shape already excludes this
            raise AssertionError(f"unreachable operator {op} for numeric attribute")
        submitted_display = str(numeric_answer)
    else:
        text_answer = str(answer)
        if op == EligibilityOperator.EQ:
            passed = text_answer == condition.text_value
        elif op == EligibilityOperator.NEQ:
            passed = text_answer != condition.text_value
        elif op == EligibilityOperator.IN:
            passed = text_answer in (condition.text_values or ())
        elif op == EligibilityOperator.NOT_IN:
            passed = text_answer not in (condition.text_values or ())
        else:  # pragma: no cover - validate_condition_shape already excludes this
            raise AssertionError(f"unreachable operator {op} for text attribute")
        submitted_display = text_answer

    return ConditionResult(
        condition_id=condition.condition_id,
        attribute=condition.attribute,
        operator=condition.operator,
        description=condition.description,
        expected=expected_display(condition),
        submitted_value=submitted_display,
        status=ConditionStatus.PASS if passed else ConditionStatus.FAIL,
        reason=None if passed else "The submitted answer does not satisfy this criterion.",
    )


def evaluate_rule(
    rule: RuleSpec, answers: Mapping[EligibilityAttribute, AnswerValue]
) -> EvaluationResult:
    """Pure evaluation — docs/ELIGIBILITY_ENGINE.md §3:

    - Every condition is evaluated independently.
    - A missing answer is `UNKNOWN`, never coerced to `PASS`/`FAIL`.
    - `NOT_ELIGIBLE` if any condition definitively `FAIL`s, even if others
      are `UNKNOWN` — a disclosed missing answer never masks a known
      disqualification, and never upgrades it to `INCOMPLETE`.
    - `ELIGIBLE` only if every condition `PASS`es.
    - Otherwise (no `FAIL`, at least one `UNKNOWN`) `INCOMPLETE`.
    - A rule with zero conditions can never be evaluated at all — see
      `app.eligibility.service`, which never treats an empty rule as
      trivially `ELIGIBLE`.
    """

    results = tuple(
        _evaluate_condition(condition, answers.get(condition.attribute))
        for condition in rule.conditions
    )

    if any(result.status == ConditionStatus.FAIL for result in results):
        outcome = EligibilityOutcome.NOT_ELIGIBLE
    elif any(result.status == ConditionStatus.UNKNOWN for result in results):
        outcome = EligibilityOutcome.INCOMPLETE
    else:
        outcome = EligibilityOutcome.ELIGIBLE

    return EvaluationResult(outcome=outcome, conditions=results)
