"""Database-level constraint tests for `EligibilityRule`/
`EligibilityCondition` — the `CHECK` constraints this domain relies on
instead of a polymorphic `entity_type`/`entity_id` pair (see
app/eligibility/models.py's module docstring), and cascade-delete
behavior. Real Postgres, per docs/TESTING.md §3.
"""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.eligibility.enums import EligibilityAttribute, EligibilityOperator
from app.eligibility.models import EligibilityCondition, EligibilityRule
from tests.test_eligibility._helpers import (
    make_condition,
    make_job,
    make_organization,
    make_rule,
    make_scheme,
    make_service,
    make_source,
    make_state,
)


def test_rule_with_zero_entities_violates_check_constraint(db_session: Session) -> None:
    source = make_source(db_session)
    db_session.add(EligibilityRule(rule_version=1, source_id=source.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_rule_with_two_entities_violates_check_constraint(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    scheme = make_scheme(db_session, organization=organization, source=source)

    db_session.add(
        EligibilityRule(job_id=job.id, scheme_id=scheme.id, rule_version=1, source_id=source.id)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_rule_with_exactly_one_entity_is_valid(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)

    rule = make_rule(db_session, source=source, job=job)
    assert rule.id is not None


def test_condition_with_no_value_at_all_violates_check_constraint(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(db_session, source=source, job=job)

    db_session.add(
        EligibilityCondition(
            rule_id=rule.id,
            attribute=EligibilityAttribute.AGE,
            operator=EligibilityOperator.GTE,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_job_cascades_to_its_rule_and_conditions(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(db_session, source=source, job=job)
    make_condition(db_session, rule)
    rule_id = rule.id

    db_session.delete(job)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(EligibilityRule, rule_id) is None
    assert db_session.query(EligibilityCondition).filter_by(rule_id=rule_id).one_or_none() is None


def test_deleting_rule_cascades_to_its_conditions(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(db_session, organization=organization, source=source)
    rule = make_rule(db_session, source=source, service=service)
    condition = make_condition(
        db_session,
        rule,
        attribute=EligibilityAttribute.INCOME_ANNUAL,
        operator=EligibilityOperator.LTE,
        numeric_value=Decimal("250000.00"),
        numeric_value_max=None,
    )
    condition_id = condition.id

    db_session.delete(rule)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(EligibilityCondition, condition_id) is None
