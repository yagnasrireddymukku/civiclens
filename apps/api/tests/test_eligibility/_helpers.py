"""Shared fixture-building helpers for Eligibility Engine tests — plain
functions, not pytest fixtures, mirroring
tests/test_documents/_helpers.py's identical pattern. Fixture data is
unambiguously fictional (docs/DATA_GOVERNANCE.md §7, docs/TESTING.md §15).
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.eligibility.enums import EligibilityAttribute, EligibilityOperator
from app.eligibility.enums import EligibilityRulePublicationStatus as RulePublicationStatus
from app.eligibility.models import EligibilityCondition, EligibilityRule
from app.geography.enums import StateStatus
from app.geography.models import State
from app.institutions.enums import OrganizationType
from app.institutions.models import Organization
from app.jobs.enums import EmploymentType, JobPublicationStatus
from app.jobs.models import Job
from app.requirements.enums import DeliveryMode
from app.schemes.enums import SchemeCategory, SchemePublicationStatus
from app.schemes.models import Scheme
from app.services.enums import ServiceCategory, ServicePublicationStatus
from app.services.models import Service
from app.sources.enums import VerificationStatus
from app.sources.models import Source


def make_state(session: Session, **overrides: Any) -> State:
    defaults: dict[str, Any] = dict(
        name="Testland", code="ZZ", slug="testland", status=StateStatus.PLANNED
    )
    defaults.update(overrides)
    state = State(**defaults)
    session.add(state)
    session.flush()
    return state


def make_source(session: Session, **overrides: Any) -> Source:
    defaults: dict[str, Any] = dict(
        url="https://example-test.invalid/notice/eligibility",
        title="Test Notice — Not Real",
        organization="Test Recruitment Board — Not Real",
        source_type="test-fixture",
        retrieved_date=datetime.date(2026, 1, 1),
    )
    defaults.update(overrides)
    source = Source(**defaults)
    session.add(source)
    session.flush()
    return source


def make_organization(session: Session, state: State, **overrides: Any) -> Organization:
    defaults: dict[str, Any] = dict(
        name="Test Recruitment Board — Not Real",
        org_type=OrganizationType.AUTONOMOUS_BODY,
        state_id=state.id,
    )
    defaults.update(overrides)
    organization = Organization(**defaults)
    session.add(organization)
    session.flush()
    return organization


def make_job(
    session: Session, *, organization: Organization, state: State, source: Source, **overrides: Any
) -> Job:
    defaults: dict[str, Any] = dict(
        slug=f"test-eligibility-job-{uuid.uuid4().hex[:8]}",
        locale="en",
        title="Test Junior Assistant Recruitment (Fixture)",
        organization_id=organization.id,
        employment_type=EmploymentType.PERMANENT,
        state_id=state.id,
        status="open",
        publication_status=JobPublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    defaults.update(overrides)
    job = Job(**defaults)
    session.add(job)
    session.flush()
    return job


def make_scheme(
    session: Session, *, organization: Organization, source: Source, **overrides: Any
) -> Scheme:
    defaults: dict[str, Any] = dict(
        slug=f"test-eligibility-scheme-{uuid.uuid4().hex[:8]}",
        locale="en",
        name="Test Merit Scholarship (Fixture)",
        organization_id=organization.id,
        category=SchemeCategory.SCHOLARSHIP,
        status="active",
        publication_status=SchemePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    defaults.update(overrides)
    scheme = Scheme(**defaults)
    session.add(scheme)
    session.flush()
    return scheme


def make_service(
    session: Session, *, organization: Organization, source: Source, **overrides: Any
) -> Service:
    defaults: dict[str, Any] = dict(
        slug=f"test-eligibility-service-{uuid.uuid4().hex[:8]}",
        locale="en",
        name="Test Old Age Pension Disbursement Service (Fixture)",
        organization_id=organization.id,
        category=ServiceCategory.SOCIAL_SECURITY,
        delivery_mode=DeliveryMode.OFFLINE,
        status="available",
        publication_status=ServicePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    defaults.update(overrides)
    service = Service(**defaults)
    session.add(service)
    session.flush()
    return service


def make_rule(
    session: Session,
    *,
    source: Source,
    job: Job | None = None,
    scheme: Scheme | None = None,
    service: Service | None = None,
    **overrides: Any,
) -> EligibilityRule:
    defaults: dict[str, Any] = dict(
        job_id=job.id if job else None,
        scheme_id=scheme.id if scheme else None,
        service_id=service.id if service else None,
        rule_version=1,
        notes="Synthetic fixture eligibility rule — not a real government criterion.",
        publication_status=RulePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    defaults.update(overrides)
    rule = EligibilityRule(**defaults)
    session.add(rule)
    session.flush()
    return rule


def make_condition(
    session: Session, rule: EligibilityRule, **overrides: Any
) -> EligibilityCondition:
    defaults: dict[str, Any] = dict(
        rule_id=rule.id,
        attribute=EligibilityAttribute.AGE,
        operator=EligibilityOperator.BETWEEN,
        description="Applicant must be between 18 and 35 years old (fictional fixture).",
        numeric_value=Decimal("18"),
        numeric_value_max=Decimal("35"),
    )
    defaults.update(overrides)
    condition = EligibilityCondition(**defaults)
    session.add(condition)
    session.flush()
    return condition
