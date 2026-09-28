"""Synthetic Eligibility Engine fixtures — for local development and
automated tests only. Never real government data
(docs/DATA_GOVERNANCE.md §7, this phase's §25).

Naming follows docs/TESTING.md §15 exactly: fake state code "ZZ"/state
name "Testland" (the same canonical fictional geography every other
domain's fixtures share), the same "Test Recruitment Board — Not Real"
organization Jobs'/Services'/Schemes'/Documents' fixtures use
(get-or-create), `.invalid` source URLs, "(Fixture)"/"Not Real" markers
throughout. `load_fixtures` refuses to run outside local/test
environments — the same second line of defense every other domain's
fixtures use.

A small, dedicated Job/Scheme/Service — own get-or-create fixtures here,
not a hard dependency on `app.jobs.fixtures`/`app.schemes.fixtures`/
`app.services.fixtures` having already run, matching
`app.documents.fixtures`'s identical independence rationale — each
carries exactly one `EligibilityRule`, together exercising every
supported attribute and operator (this phase's §31 test-matrix intent,
applied to fixture data rather than only unit-test dataclasses):

- Job rule: `AGE BETWEEN 18-35` + `RESIDENCE_STATE EQ "ZZ"`.
- Scheme rule (a fictional scholarship): `EDUCATION_LEVEL IN
  (UNDERGRADUATE, POSTGRADUATE)` + `ACADEMIC_PERCENTAGE GTE 60.00`.
- Service rule: `INCOME_ANNUAL LTE 250000.00` + `CATEGORY NOT_IN
  ("EXCLUDED_CATEGORY_FIXTURE",)`.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.eligibility.enums import EligibilityAttribute, EligibilityOperator
from app.eligibility.enums import EligibilityRulePublicationStatus as RulePublicationStatus
from app.eligibility.models import EligibilityCondition, EligibilityRule
from app.geography.enums import StateStatus
from app.geography.models import District, State
from app.institutions.enums import OrganizationType
from app.institutions.models import Department, Organization
from app.jobs.enums import EmploymentType, JobPublicationStatus
from app.jobs.models import Job
from app.requirements.enums import DeliveryMode
from app.schemes.enums import SchemeCategory, SchemePublicationStatus
from app.schemes.models import Scheme
from app.services.enums import ServiceCategory, ServicePublicationStatus
from app.services.models import Service
from app.sources.enums import VerificationStatus
from app.sources.models import Source

_ALLOWED_ENVIRONMENTS = ("local", "test")
_VERIFIED_AT = datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC)


def _fixture_state(session: Session) -> State:
    existing = session.query(State).filter_by(code="ZZ").one_or_none()
    if existing is not None:
        return existing
    state = State(name="Testland", code="ZZ", slug="testland", status=StateStatus.PLANNED)
    session.add(state)
    session.flush()
    return state


def _fixture_district(session: Session, state: State) -> District:
    existing = session.query(District).filter_by(state_id=state.id, code="SB").one_or_none()
    if existing is not None:
        return existing
    district = District(state_id=state.id, name="Sampleburg", code="SB", slug="sampleburg")
    session.add(district)
    session.flush()
    return district


def _fixture_organization(session: Session, state: State) -> Organization:
    existing = (
        session.query(Organization)
        .filter_by(name="Test Recruitment Board — Not Real")
        .one_or_none()
    )
    if existing is not None:
        return existing
    organization = Organization(
        name="Test Recruitment Board — Not Real",
        org_type=OrganizationType.AUTONOMOUS_BODY,
        state_id=state.id,
    )
    session.add(organization)
    session.flush()
    return organization


def _fixture_department(session: Session, state: State, organization: Organization) -> Department:
    existing = (
        session.query(Department)
        .filter_by(organization_id=organization.id, name="Test Department — Not Real")
        .one_or_none()
    )
    if existing is not None:
        return existing
    department = Department(
        name="Test Department — Not Real", organization_id=organization.id, state_id=state.id
    )
    session.add(department)
    session.flush()
    return department


def _fixture_source(slug_suffix: str) -> Source:
    return Source(
        url=f"https://example-test.invalid/notice/eligibility-fixtures-{slug_suffix}",
        title="Test Notice — Not Real",
        organization="Test Recruitment Board — Not Real",
        source_type="test-fixture",
        retrieved_date=datetime.date(2026, 1, 1),
    )


def _fixture_job(
    session: Session, *, organization: Organization, department: Department, state: State
) -> Job:
    existing = session.query(Job).filter_by(slug="test-civiclens-eligibility-job-001").one_or_none()
    if existing is not None:
        return existing

    source = _fixture_source("job")
    session.add(source)
    session.flush()

    job = Job(
        slug="test-civiclens-eligibility-job-001",
        locale="en",
        title="Test Junior Assistant Recruitment (Fixture)",
        organization_id=organization.id,
        department_id=department.id,
        summary="A fictional job used only to exercise the Eligibility Engine.",
        employment_type=EmploymentType.PERMANENT,
        state_id=state.id,
        status="open",
        publication_status=JobPublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=_VERIFIED_AT,
    )
    session.add(job)
    session.flush()
    return job


def _fixture_scheme(
    session: Session, *, organization: Organization, department: Department, state: State
) -> Scheme:
    existing = (
        session.query(Scheme).filter_by(slug="test-civiclens-eligibility-scheme-001").one_or_none()
    )
    if existing is not None:
        return existing

    source = _fixture_source("scheme")
    session.add(source)
    session.flush()

    scheme = Scheme(
        slug="test-civiclens-eligibility-scheme-001",
        locale="en",
        name="Test Merit Scholarship (Fixture)",
        short_description="A fictional scholarship used only to exercise the Eligibility Engine.",
        organization_id=organization.id,
        department_id=department.id,
        category=SchemeCategory.SCHOLARSHIP,
        state_id=state.id,
        status="active",
        publication_status=SchemePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=_VERIFIED_AT,
    )
    session.add(scheme)
    session.flush()
    return scheme


def _fixture_service(
    session: Session, *, organization: Organization, department: Department, state: State
) -> Service:
    existing = (
        session.query(Service)
        .filter_by(slug="test-civiclens-eligibility-service-001")
        .one_or_none()
    )
    if existing is not None:
        return existing

    source = _fixture_source("service")
    session.add(source)
    session.flush()

    service = Service(
        slug="test-civiclens-eligibility-service-001",
        locale="en",
        name="Test Old Age Pension Disbursement Service (Fixture)",
        short_description="A fictional service used only to exercise the Eligibility Engine.",
        organization_id=organization.id,
        department_id=department.id,
        category=ServiceCategory.SOCIAL_SECURITY,
        delivery_mode=DeliveryMode.OFFLINE,
        state_id=state.id,
        status="available",
        publication_status=ServicePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=_VERIFIED_AT,
    )
    session.add(service)
    session.flush()
    return service


def _get_or_create_rule(
    session: Session,
    *,
    job_id: uuid.UUID | None = None,
    scheme_id: uuid.UUID | None = None,
    service_id: uuid.UUID | None = None,
    build_conditions: Callable[[EligibilityRule], None],
) -> EligibilityRule:
    query = session.query(EligibilityRule)
    if job_id is not None:
        query = query.filter_by(job_id=job_id)
    elif scheme_id is not None:
        query = query.filter_by(scheme_id=scheme_id)
    else:
        query = query.filter_by(service_id=service_id)
    existing = query.one_or_none()
    if existing is not None:
        return existing

    slug_suffix = "job" if job_id is not None else "scheme" if scheme_id is not None else "service"
    source = _fixture_source(f"rule-{slug_suffix}")
    session.add(source)
    session.flush()

    rule = EligibilityRule(
        job_id=job_id,
        scheme_id=scheme_id,
        service_id=service_id,
        rule_version=1,
        notes="Synthetic fixture eligibility rule — not a real government criterion.",
        publication_status=RulePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=_VERIFIED_AT,
    )
    session.add(rule)
    session.flush()
    build_conditions(rule)
    return rule


def load_fixtures(session: Session) -> None:
    """Inserts a small fictional Job/Scheme/Service, each carrying one
    `EligibilityRule`, together exercising every supported attribute and
    operator — see module docstring. Refuses to run unless `APP_ENV` is
    "local" or "test"."""

    settings = get_settings()
    if settings.app_env not in _ALLOWED_ENVIRONMENTS:
        raise RuntimeError(
            f"Refusing to load eligibility fixtures: APP_ENV={settings.app_env!r} is not one of "
            f"{_ALLOWED_ENVIRONMENTS}. Fixtures must never reach a staging/production database."
        )

    state = _fixture_state(session)
    district = _fixture_district(session, state)
    organization = _fixture_organization(session, state)
    department = _fixture_department(session, state, organization)

    job = _fixture_job(session, organization=organization, department=department, state=state)
    scheme = _fixture_scheme(session, organization=organization, department=department, state=state)
    service = _fixture_service(
        session, organization=organization, department=department, state=state
    )
    # `district` is not referenced by any entity above (each is scoped to
    # the whole fictional state) — kept for parity with sibling fixture
    # modules that do use it, and available to a future addition here.
    del district

    def _job_conditions(rule: EligibilityRule) -> None:
        session.add_all(
            [
                EligibilityCondition(
                    rule_id=rule.id,
                    attribute=EligibilityAttribute.AGE,
                    operator=EligibilityOperator.BETWEEN,
                    description=(
                        "Applicant must be between 18 and 35 years old (fictional fixture)."
                    ),
                    numeric_value=Decimal("18"),
                    numeric_value_max=Decimal("35"),
                ),
                EligibilityCondition(
                    rule_id=rule.id,
                    attribute=EligibilityAttribute.RESIDENCE_STATE,
                    operator=EligibilityOperator.EQ,
                    description="Applicant must be a resident of Testland (fictional fixture).",
                    text_value="ZZ",
                ),
            ]
        )

    def _scheme_conditions(rule: EligibilityRule) -> None:
        session.add_all(
            [
                EligibilityCondition(
                    rule_id=rule.id,
                    attribute=EligibilityAttribute.EDUCATION_LEVEL,
                    operator=EligibilityOperator.IN,
                    description=(
                        "Applicant must be enrolled in an undergraduate or postgraduate "
                        "program (fictional fixture)."
                    ),
                    text_values=["UNDERGRADUATE", "POSTGRADUATE"],
                ),
                EligibilityCondition(
                    rule_id=rule.id,
                    attribute=EligibilityAttribute.ACADEMIC_PERCENTAGE,
                    operator=EligibilityOperator.GTE,
                    description=(
                        "Applicant must have scored at least 60% in the qualifying "
                        "examination (fictional fixture)."
                    ),
                    numeric_value=Decimal("60.00"),
                ),
            ]
        )

    def _service_conditions(rule: EligibilityRule) -> None:
        session.add_all(
            [
                EligibilityCondition(
                    rule_id=rule.id,
                    attribute=EligibilityAttribute.INCOME_ANNUAL,
                    operator=EligibilityOperator.LTE,
                    description=(
                        "Applicant's annual household income must not exceed ₹2,50,000 "
                        "(fictional fixture)."
                    ),
                    numeric_value=Decimal("250000.00"),
                ),
                EligibilityCondition(
                    rule_id=rule.id,
                    attribute=EligibilityAttribute.CATEGORY,
                    operator=EligibilityOperator.NOT_IN,
                    description=(
                        "Applicant must not belong to an excluded category (fictional fixture)."
                    ),
                    text_values=["EXCLUDED_CATEGORY_FIXTURE"],
                ),
            ]
        )

    _get_or_create_rule(session, job_id=job.id, build_conditions=_job_conditions)
    _get_or_create_rule(session, scheme_id=scheme.id, build_conditions=_scheme_conditions)
    _get_or_create_rule(session, service_id=service.id, build_conditions=_service_conditions)

    session.commit()
