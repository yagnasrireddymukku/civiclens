"""The Eligibility Engine's deterministic test matrix — docs/TESTING.md
§6 ("100% branch coverage on the evaluation function specifically, as an
explicit CI gate"). Pure unit tests, no database, no network — every
operator, both BETWEEN boundaries, every outcome combination, malformed-
rule rejection, and reproducibility.
"""

import uuid
from decimal import Decimal

import pytest

from app.eligibility.enums import (
    ConditionStatus,
    EligibilityAttribute,
    EligibilityOperator,
    EligibilityOutcome,
)
from app.eligibility.evaluator import (
    ConditionSpec,
    InvalidEligibilityRuleError,
    RuleSpec,
    evaluate_rule,
)

RULE_ID = uuid.uuid4()


def _age_between_18_35() -> ConditionSpec:
    return ConditionSpec(
        condition_id=uuid.uuid4(),
        attribute=EligibilityAttribute.AGE,
        operator=EligibilityOperator.BETWEEN,
        description="Age between 18 and 35.",
        numeric_value=Decimal("18"),
        numeric_value_max=Decimal("35"),
    )


def _income_lte_250000() -> ConditionSpec:
    return ConditionSpec(
        condition_id=uuid.uuid4(),
        attribute=EligibilityAttribute.INCOME_ANNUAL,
        operator=EligibilityOperator.LTE,
        description="Income at most 250000.",
        numeric_value=Decimal("250000.00"),
    )


def _percentage_gte_60() -> ConditionSpec:
    return ConditionSpec(
        condition_id=uuid.uuid4(),
        attribute=EligibilityAttribute.ACADEMIC_PERCENTAGE,
        operator=EligibilityOperator.GTE,
        description="Percentage at least 60.",
        numeric_value=Decimal("60.00"),
    )


def _cgpa_eq_8() -> ConditionSpec:
    return ConditionSpec(
        condition_id=uuid.uuid4(),
        attribute=EligibilityAttribute.ACADEMIC_CGPA,
        operator=EligibilityOperator.EQ,
        description="CGPA exactly 8.",
        numeric_value=Decimal("8.00"),
    )


def _age_neq_0() -> ConditionSpec:
    return ConditionSpec(
        condition_id=uuid.uuid4(),
        attribute=EligibilityAttribute.AGE,
        operator=EligibilityOperator.NEQ,
        description="Age not zero.",
        numeric_value=Decimal("0"),
    )


def _education_level_in() -> ConditionSpec:
    return ConditionSpec(
        condition_id=uuid.uuid4(),
        attribute=EligibilityAttribute.EDUCATION_LEVEL,
        operator=EligibilityOperator.IN,
        description="Education level is UG or PG.",
        text_values=("UNDERGRADUATE", "POSTGRADUATE"),
    )


def _category_not_in() -> ConditionSpec:
    return ConditionSpec(
        condition_id=uuid.uuid4(),
        attribute=EligibilityAttribute.CATEGORY,
        operator=EligibilityOperator.NOT_IN,
        description="Category is not excluded.",
        text_values=("EXCLUDED",),
    )


def _residence_state_eq_zz() -> ConditionSpec:
    return ConditionSpec(
        condition_id=uuid.uuid4(),
        attribute=EligibilityAttribute.RESIDENCE_STATE,
        operator=EligibilityOperator.EQ,
        description="Resident of ZZ.",
        text_value="ZZ",
    )


def _residence_state_neq_zz() -> ConditionSpec:
    return ConditionSpec(
        condition_id=uuid.uuid4(),
        attribute=EligibilityAttribute.RESIDENCE_STATE,
        operator=EligibilityOperator.NEQ,
        description="Not resident of ZZ.",
        text_value="ZZ",
    )


class TestNumericOperators:
    def test_between_inside_range_passes(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(),))
        result = evaluate_rule(rule, {EligibilityAttribute.AGE: Decimal("25")})
        assert result.outcome == EligibilityOutcome.ELIGIBLE
        assert result.conditions[0].status == ConditionStatus.PASS

    def test_between_lower_boundary_inclusive(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(),))
        result = evaluate_rule(rule, {EligibilityAttribute.AGE: Decimal("18")})
        assert result.conditions[0].status == ConditionStatus.PASS

    def test_between_upper_boundary_inclusive(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(),))
        result = evaluate_rule(rule, {EligibilityAttribute.AGE: Decimal("35")})
        assert result.conditions[0].status == ConditionStatus.PASS

    def test_between_just_below_lower_boundary_fails(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(),))
        result = evaluate_rule(rule, {EligibilityAttribute.AGE: Decimal("17")})
        assert result.outcome == EligibilityOutcome.NOT_ELIGIBLE
        assert result.conditions[0].status == ConditionStatus.FAIL

    def test_between_just_above_upper_boundary_fails(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(),))
        result = evaluate_rule(rule, {EligibilityAttribute.AGE: Decimal("36")})
        assert result.conditions[0].status == ConditionStatus.FAIL

    def test_lte_at_boundary_passes(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_income_lte_250000(),))
        result = evaluate_rule(rule, {EligibilityAttribute.INCOME_ANNUAL: Decimal("250000.00")})
        assert result.conditions[0].status == ConditionStatus.PASS

    def test_lte_above_boundary_fails(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_income_lte_250000(),))
        result = evaluate_rule(rule, {EligibilityAttribute.INCOME_ANNUAL: Decimal("250000.01")})
        assert result.conditions[0].status == ConditionStatus.FAIL

    def test_gte_at_boundary_passes(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_percentage_gte_60(),))
        result = evaluate_rule(rule, {EligibilityAttribute.ACADEMIC_PERCENTAGE: Decimal("60.00")})
        assert result.conditions[0].status == ConditionStatus.PASS

    def test_gte_below_boundary_fails(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_percentage_gte_60(),))
        result = evaluate_rule(rule, {EligibilityAttribute.ACADEMIC_PERCENTAGE: Decimal("59.99")})
        assert result.conditions[0].status == ConditionStatus.FAIL

    def test_eq_matching_value_passes(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_cgpa_eq_8(),))
        result = evaluate_rule(rule, {EligibilityAttribute.ACADEMIC_CGPA: Decimal("8.00")})
        assert result.conditions[0].status == ConditionStatus.PASS

    def test_eq_different_value_fails(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_cgpa_eq_8(),))
        result = evaluate_rule(rule, {EligibilityAttribute.ACADEMIC_CGPA: Decimal("7.50")})
        assert result.conditions[0].status == ConditionStatus.FAIL

    def test_neq_different_value_passes(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_age_neq_0(),))
        result = evaluate_rule(rule, {EligibilityAttribute.AGE: Decimal("25")})
        assert result.conditions[0].status == ConditionStatus.PASS

    def test_neq_matching_value_fails(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_age_neq_0(),))
        result = evaluate_rule(rule, {EligibilityAttribute.AGE: Decimal("0")})
        assert result.conditions[0].status == ConditionStatus.FAIL

    def test_decimal_precision_is_exact_not_float_lossy(self) -> None:
        # 59.99 must never be nudged to "pass" a >=60.00 threshold by
        # float error (this phase's §B) — Decimal comparison is exact.
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_percentage_gte_60(),))
        result = evaluate_rule(
            rule, {EligibilityAttribute.ACADEMIC_PERCENTAGE: Decimal("59.999999")}
        )
        assert result.conditions[0].status == ConditionStatus.FAIL

    def test_string_answer_for_numeric_attribute_is_coerced(self) -> None:
        # The API layer always sends a Decimal for numeric attributes,
        # but the evaluator accepts a numeric string defensively too.
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_percentage_gte_60(),))
        result = evaluate_rule(rule, {EligibilityAttribute.ACADEMIC_PERCENTAGE: "75"})
        assert result.conditions[0].status == ConditionStatus.PASS


class TestTextOperators:
    def test_in_matching_value_passes(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_education_level_in(),))
        result = evaluate_rule(rule, {EligibilityAttribute.EDUCATION_LEVEL: "UNDERGRADUATE"})
        assert result.conditions[0].status == ConditionStatus.PASS

    def test_in_non_matching_value_fails(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_education_level_in(),))
        result = evaluate_rule(rule, {EligibilityAttribute.EDUCATION_LEVEL: "SCHOOL"})
        assert result.conditions[0].status == ConditionStatus.FAIL

    def test_not_in_non_matching_value_passes(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_category_not_in(),))
        result = evaluate_rule(rule, {EligibilityAttribute.CATEGORY: "GENERAL"})
        assert result.conditions[0].status == ConditionStatus.PASS

    def test_not_in_matching_value_fails(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_category_not_in(),))
        result = evaluate_rule(rule, {EligibilityAttribute.CATEGORY: "EXCLUDED"})
        assert result.conditions[0].status == ConditionStatus.FAIL

    def test_text_eq_matching_value_passes(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_residence_state_eq_zz(),))
        result = evaluate_rule(rule, {EligibilityAttribute.RESIDENCE_STATE: "ZZ"})
        assert result.conditions[0].status == ConditionStatus.PASS

    def test_text_eq_non_matching_value_fails(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_residence_state_eq_zz(),))
        result = evaluate_rule(rule, {EligibilityAttribute.RESIDENCE_STATE: "YY"})
        assert result.conditions[0].status == ConditionStatus.FAIL

    def test_text_neq_non_matching_value_passes(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_residence_state_neq_zz(),))
        result = evaluate_rule(rule, {EligibilityAttribute.RESIDENCE_STATE: "YY"})
        assert result.conditions[0].status == ConditionStatus.PASS


class TestMissingAnswers:
    def test_missing_answer_is_unknown_not_pass_or_fail(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(),))
        result = evaluate_rule(rule, {})
        assert result.conditions[0].status == ConditionStatus.UNKNOWN
        assert result.outcome == EligibilityOutcome.INCOMPLETE

    def test_explicit_none_answer_is_unknown(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(),))
        result = evaluate_rule(rule, {EligibilityAttribute.AGE: None})
        assert result.conditions[0].status == ConditionStatus.UNKNOWN


class TestOverallOutcome:
    def test_all_pass_is_eligible(self) -> None:
        rule = RuleSpec(
            rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(), _income_lte_250000())
        )
        result = evaluate_rule(
            rule,
            {
                EligibilityAttribute.AGE: Decimal("25"),
                EligibilityAttribute.INCOME_ANNUAL: Decimal("100000"),
            },
        )
        assert result.outcome == EligibilityOutcome.ELIGIBLE

    def test_one_fail_is_not_eligible_even_with_others_passing(self) -> None:
        rule = RuleSpec(
            rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(), _income_lte_250000())
        )
        result = evaluate_rule(
            rule,
            {
                EligibilityAttribute.AGE: Decimal("25"),
                EligibilityAttribute.INCOME_ANNUAL: Decimal("999999"),
            },
        )
        assert result.outcome == EligibilityOutcome.NOT_ELIGIBLE

    def test_fail_outranks_unknown_never_masked_as_incomplete(self) -> None:
        # A disclosed missing answer must never hide or soften a known
        # disqualification (docs/ELIGIBILITY_ENGINE.md §3).
        rule = RuleSpec(
            rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(), _income_lte_250000())
        )
        result = evaluate_rule(
            rule, {EligibilityAttribute.AGE: Decimal("99")}
        )  # income missing, age fails
        assert result.outcome == EligibilityOutcome.NOT_ELIGIBLE
        statuses = {c.attribute: c.status for c in result.conditions}
        assert statuses[EligibilityAttribute.AGE] == ConditionStatus.FAIL
        assert statuses[EligibilityAttribute.INCOME_ANNUAL] == ConditionStatus.UNKNOWN

    def test_no_fail_with_one_unknown_is_incomplete(self) -> None:
        rule = RuleSpec(
            rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(), _income_lte_250000())
        )
        result = evaluate_rule(rule, {EligibilityAttribute.AGE: Decimal("25")})
        assert result.outcome == EligibilityOutcome.INCOMPLETE

    def test_reproducible_for_identical_inputs(self) -> None:
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=(_age_between_18_35(),))
        answers = {EligibilityAttribute.AGE: Decimal("25")}
        first = evaluate_rule(rule, answers)
        second = evaluate_rule(rule, answers)
        assert first == second


class TestMalformedRuleRejection:
    def test_between_missing_upper_bound_is_rejected(self) -> None:
        with pytest.raises(InvalidEligibilityRuleError):
            ConditionSpec(
                condition_id=uuid.uuid4(),
                attribute=EligibilityAttribute.AGE,
                operator=EligibilityOperator.BETWEEN,
                description=None,
                numeric_value=Decimal("18"),
            )

    def test_between_lower_bound_above_upper_bound_is_rejected(self) -> None:
        with pytest.raises(InvalidEligibilityRuleError):
            ConditionSpec(
                condition_id=uuid.uuid4(),
                attribute=EligibilityAttribute.AGE,
                operator=EligibilityOperator.BETWEEN,
                description=None,
                numeric_value=Decimal("50"),
                numeric_value_max=Decimal("18"),
            )

    def test_gte_without_numeric_value_is_rejected(self) -> None:
        with pytest.raises(InvalidEligibilityRuleError):
            ConditionSpec(
                condition_id=uuid.uuid4(),
                attribute=EligibilityAttribute.AGE,
                operator=EligibilityOperator.GTE,
                description=None,
            )

    def test_in_operator_on_numeric_attribute_is_rejected(self) -> None:
        with pytest.raises(InvalidEligibilityRuleError):
            ConditionSpec(
                condition_id=uuid.uuid4(),
                attribute=EligibilityAttribute.AGE,
                operator=EligibilityOperator.IN,
                description=None,
                text_values=("18", "19"),
            )

    def test_in_without_text_values_is_rejected(self) -> None:
        with pytest.raises(InvalidEligibilityRuleError):
            ConditionSpec(
                condition_id=uuid.uuid4(),
                attribute=EligibilityAttribute.CATEGORY,
                operator=EligibilityOperator.IN,
                description=None,
                text_values=(),
            )

    def test_between_operator_on_text_attribute_is_rejected(self) -> None:
        with pytest.raises(InvalidEligibilityRuleError):
            ConditionSpec(
                condition_id=uuid.uuid4(),
                attribute=EligibilityAttribute.CATEGORY,
                operator=EligibilityOperator.BETWEEN,
                description=None,
                numeric_value=Decimal("1"),
                numeric_value_max=Decimal("2"),
            )

    def test_eq_on_text_attribute_without_text_value_is_rejected(self) -> None:
        with pytest.raises(InvalidEligibilityRuleError):
            ConditionSpec(
                condition_id=uuid.uuid4(),
                attribute=EligibilityAttribute.CATEGORY,
                operator=EligibilityOperator.EQ,
                description=None,
            )


class TestEmptyRule:
    def test_rule_with_no_conditions_evaluates_to_eligible_vacuously(self) -> None:
        # `evaluate_rule` itself has no concept of "no rule available" —
        # that's `app.eligibility.service.get_evaluable_rule`'s job,
        # which never hands a zero-condition rule to this function at
        # all (see its own test in test_service.py). This test documents
        # the pure function's actual (vacuous-truth) behavior in
        # isolation, so the guard living in the service layer is not an
        # accident of what this function happens to do.
        rule = RuleSpec(rule_id=RULE_ID, rule_version=1, conditions=())
        result = evaluate_rule(rule, {})
        assert result.outcome == EligibilityOutcome.ELIGIBLE
        assert result.conditions == ()
