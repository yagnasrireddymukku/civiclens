"""The critical safety property this phase requires: the LLM can never
change a deterministic Eligibility Engine result. `explain_eligibility`
calls `app.eligibility.service` unmodified and only ever *phrases* the
outcome it returns — this file proves that even a provider that
actively tries to state a different outcome cannot make it through.
"""

import asyncio
from decimal import Decimal

from sqlalchemy.orm import Session

from app.ai.eligibility_explainer import explain_eligibility
from app.ai.enums import EligibilityExplanationStatus
from app.eligibility.enums import (
    EligibilityAttribute,
    EligibilityEntityType,
    EligibilityOperator,
    EligibilityOutcome,
)
from app.eligibility.schemas import EligibilityAnswers
from tests.test_ai._helpers import FakeLLMProvider
from tests.test_eligibility._helpers import (
    make_condition,
    make_job,
    make_organization,
    make_rule,
    make_source,
    make_state,
)


def _sync(coro):
    return asyncio.run(coro)


def _job_with_age_rule(db_session: Session):
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(db_session, source=source, job=job)
    make_condition(db_session, rule)  # AGE BETWEEN 18-35, see _helpers' default
    return job, rule


def test_entity_not_found(db_session: Session) -> None:
    result = _sync(
        explain_eligibility(
            db_session,
            entity_type=EligibilityEntityType.JOB,
            entity_slug="does-not-exist",
            answers=EligibilityAnswers(),
            llm_provider=None,
        )
    )
    assert result.status == EligibilityExplanationStatus.ENTITY_NOT_FOUND
    assert result.outcome is None


def test_not_supported_when_no_evaluable_rule_exists(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)

    result = _sync(
        explain_eligibility(
            db_session,
            entity_type=EligibilityEntityType.JOB,
            entity_slug=job.slug,
            answers=EligibilityAnswers(),
            llm_provider=None,
        )
    )
    assert result.status == EligibilityExplanationStatus.NOT_SUPPORTED
    assert "cannot currently be determined" in result.message


def test_explained_without_llm_uses_template_and_preserves_outcome(db_session: Session) -> None:
    job, rule = _job_with_age_rule(db_session)

    result = _sync(
        explain_eligibility(
            db_session,
            entity_type=EligibilityEntityType.JOB,
            entity_slug=job.slug,
            answers=EligibilityAnswers(age=25, residence_state_code="ZZ"),
            llm_provider=None,
        )
    )

    assert result.status == EligibilityExplanationStatus.EXPLAINED
    assert result.outcome == EligibilityOutcome.ELIGIBLE
    assert result.rule_id == rule.id
    assert result.explanation is not None


def test_llm_phrasing_used_when_it_matches_the_real_outcome(db_session: Session) -> None:
    job, _rule = _job_with_age_rule(db_session)
    llm = FakeLLMProvider(
        '{"explanation": "You meet the age and residence requirements.", '
        '"stated_outcome": "ELIGIBLE"}'
    )

    result = _sync(
        explain_eligibility(
            db_session,
            entity_type=EligibilityEntityType.JOB,
            entity_slug=job.slug,
            answers=EligibilityAnswers(age=25, residence_state_code="ZZ"),
            llm_provider=llm,
        )
    )

    assert result.outcome == EligibilityOutcome.ELIGIBLE
    assert result.explanation == "You meet the age and residence requirements."


def test_llm_contradicting_the_real_outcome_is_discarded(db_session: Session) -> None:
    """The critical test: a submitted age of 90 fails the 18-35 rule
    (NOT_ELIGIBLE), but the fake LLM tries to claim ELIGIBLE anyway —
    its phrasing must never reach the user, and the real outcome must
    never change."""

    job, _rule = _job_with_age_rule(db_session)
    lying_llm = FakeLLMProvider(
        '{"explanation": "Great news, you are eligible!", "stated_outcome": "ELIGIBLE"}'
    )

    result = _sync(
        explain_eligibility(
            db_session,
            entity_type=EligibilityEntityType.JOB,
            entity_slug=job.slug,
            answers=EligibilityAnswers(age=90, residence_state_code="ZZ"),
            llm_provider=lying_llm,
        )
    )

    assert result.outcome == EligibilityOutcome.NOT_ELIGIBLE  # unchanged, still correct
    assert result.explanation is not None
    assert "Great news, you are eligible!" not in result.explanation
    assert "Not met" in result.explanation  # the honest template fallback


def test_llm_provider_failure_falls_back_to_template(db_session: Session) -> None:
    job, _rule = _job_with_age_rule(db_session)
    failing_llm = FakeLLMProvider("irrelevant", raise_error=True)

    result = _sync(
        explain_eligibility(
            db_session,
            entity_type=EligibilityEntityType.JOB,
            entity_slug=job.slug,
            answers=EligibilityAnswers(age=25, residence_state_code="ZZ"),
            llm_provider=failing_llm,
        )
    )

    assert result.status == EligibilityExplanationStatus.EXPLAINED
    assert result.outcome == EligibilityOutcome.ELIGIBLE
    assert result.explanation is not None


def test_llm_unparseable_response_falls_back_to_template(db_session: Session) -> None:
    job, _rule = _job_with_age_rule(db_session)
    garbled_llm = FakeLLMProvider("not json")

    result = _sync(
        explain_eligibility(
            db_session,
            entity_type=EligibilityEntityType.JOB,
            entity_slug=job.slug,
            answers=EligibilityAnswers(age=25, residence_state_code="ZZ"),
            llm_provider=garbled_llm,
        )
    )

    assert result.status == EligibilityExplanationStatus.EXPLAINED
    assert result.outcome == EligibilityOutcome.ELIGIBLE


def test_incomplete_outcome_when_answer_missing(db_session: Session) -> None:
    job, _rule = _job_with_age_rule(db_session)

    result = _sync(
        explain_eligibility(
            db_session,
            entity_type=EligibilityEntityType.JOB,
            entity_slug=job.slug,
            answers=EligibilityAnswers(),
            llm_provider=None,
        )
    )

    assert result.outcome == EligibilityOutcome.INCOMPLETE


def test_decimal_answers_are_accepted(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(db_session, source=source, job=job)
    make_condition(
        db_session,
        rule,
        attribute=EligibilityAttribute.INCOME_ANNUAL,
        operator=EligibilityOperator.LTE,
        numeric_value=Decimal("250000.00"),
        numeric_value_max=None,
        description="Income at most 250000.",
    )

    result = _sync(
        explain_eligibility(
            db_session,
            entity_type=EligibilityEntityType.JOB,
            entity_slug=job.slug,
            answers=EligibilityAnswers(income_annual=Decimal("100000.00")),
            llm_provider=None,
        )
    )

    assert result.outcome == EligibilityOutcome.ELIGIBLE
