"""Eligibility service-layer tests: entity resolution (reusing each
domain's own visibility rule), the evaluability gate (stricter than the
standard display-visibility rule — VERIFIED only, see
app/eligibility/models.py's module docstring), and answer-map conversion.
"""

import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.eligibility import service
from app.eligibility.enums import EligibilityAttribute, EligibilityEntityType
from app.eligibility.enums import EligibilityRulePublicationStatus as RulePublicationStatus
from app.eligibility.schemas import EligibilityAnswers
from app.jobs.enums import JobPublicationStatus
from app.schemes.enums import EducationLevel
from app.sources.enums import VerificationStatus
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


def test_resolve_entity_finds_visible_job_by_slug(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)

    resolved = service.resolve_entity(db_session, EligibilityEntityType.JOB, job.slug)

    assert resolved is not None
    assert resolved.entity_id == job.id
    assert resolved.name == job.title


def test_resolve_entity_returns_none_for_unpublished_job(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        publication_status=JobPublicationStatus.DRAFT,
    )

    assert service.resolve_entity(db_session, EligibilityEntityType.JOB, job.slug) is None


def test_resolve_entity_returns_none_for_unknown_slug(db_session: Session) -> None:
    assert service.resolve_entity(db_session, EligibilityEntityType.JOB, "no-such-job-slug") is None


def test_resolve_entity_finds_scheme_and_service(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)
    svc = make_service(db_session, organization=organization, source=source)

    resolved_scheme = service.resolve_entity(db_session, EligibilityEntityType.SCHEME, scheme.slug)
    resolved_service = service.resolve_entity(db_session, EligibilityEntityType.SERVICE, svc.slug)

    assert resolved_scheme is not None and resolved_scheme.entity_id == scheme.id
    assert resolved_service is not None and resolved_service.entity_id == svc.id


def test_get_evaluable_rule_returns_verified_published_rule(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(db_session, source=source, job=job)
    make_condition(db_session, rule)

    row = service.get_evaluable_rule(db_session, EligibilityEntityType.JOB, job.id)

    assert row is not None
    assert row.rule.id == rule.id


def test_get_evaluable_rule_excludes_needs_review(db_session: Session) -> None:
    # Stricter than the standard display-visibility rule (VERIFIED OR
    # NEEDS_REVIEW) — an evaluation is a claim of fact, so NEEDS_REVIEW
    # must never be evaluable.
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(
        db_session, source=source, job=job, verification_status=VerificationStatus.NEEDS_REVIEW
    )
    make_condition(db_session, rule)

    assert service.get_evaluable_rule(db_session, EligibilityEntityType.JOB, job.id) is None


def test_get_evaluable_rule_excludes_unverified(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(
        db_session, source=source, job=job, verification_status=VerificationStatus.UNVERIFIED
    )
    make_condition(db_session, rule)

    assert service.get_evaluable_rule(db_session, EligibilityEntityType.JOB, job.id) is None


def test_get_evaluable_rule_excludes_expired(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(
        db_session, source=source, job=job, verification_status=VerificationStatus.EXPIRED
    )
    make_condition(db_session, rule)

    assert service.get_evaluable_rule(db_session, EligibilityEntityType.JOB, job.id) is None


def test_get_evaluable_rule_excludes_draft_publication_status(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(
        db_session, source=source, job=job, publication_status=RulePublicationStatus.DRAFT
    )
    make_condition(db_session, rule)

    assert service.get_evaluable_rule(db_session, EligibilityEntityType.JOB, job.id) is None


def test_get_evaluable_rule_excludes_soft_deleted_rule(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(
        db_session,
        source=source,
        job=job,
        deleted_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    make_condition(db_session, rule)

    assert service.get_evaluable_rule(db_session, EligibilityEntityType.JOB, job.id) is None


def test_get_evaluable_rule_excludes_zero_condition_rule(db_session: Session) -> None:
    # Never a silent authoritative outcome from inadequate data
    # (this phase's §D) — a published, verified rule with no conditions
    # can't express anything.
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    make_rule(db_session, source=source, job=job)

    assert service.get_evaluable_rule(db_session, EligibilityEntityType.JOB, job.id) is None


def test_build_answer_map_converts_enum_and_skips_none() -> None:
    answers = EligibilityAnswers(
        age=25,
        income_annual=None,
        education_level=EducationLevel.UNDERGRADUATE,
        academic_percentage=Decimal("75.50"),
        residence_state_code="ZZ",
    )

    answer_map = service.build_answer_map(answers)

    assert answer_map[EligibilityAttribute.AGE] == 25
    assert answer_map[EligibilityAttribute.EDUCATION_LEVEL] == "UNDERGRADUATE"
    assert answer_map[EligibilityAttribute.ACADEMIC_PERCENTAGE] == Decimal("75.50")
    assert answer_map[EligibilityAttribute.RESIDENCE_STATE] == "ZZ"
    assert EligibilityAttribute.INCOME_ANNUAL not in answer_map
    assert EligibilityAttribute.ACADEMIC_CGPA not in answer_map
    assert EligibilityAttribute.CATEGORY not in answer_map
