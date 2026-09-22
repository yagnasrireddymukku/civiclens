"""Shared fixture-building helpers for Schemes domain tests — plain
functions, not pytest fixtures, mirroring
tests/test_services/_helpers.py's identical pattern. Fixture data is
unambiguously fictional (docs/DATA_GOVERNANCE.md §7, docs/TESTING.md §15).
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.geography.enums import StateStatus
from app.geography.models import District, State
from app.institutions.enums import OrganizationType
from app.institutions.models import Department, Organization
from app.requirements.enums import ApplicationChannelType, RequirementType
from app.schemes.enums import BenefitType, SchemeCategory, SchemePublicationStatus
from app.schemes.models import (
    Scheme,
    SchemeApplicationMethod,
    SchemeBenefit,
    SchemeRelatedService,
    SchemeRequiredDocument,
    SchemeRequirement,
)
from app.services.enums import DeliveryMode, ServiceCategory, ServicePublicationStatus
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


def make_district(session: Session, state: State, **overrides: Any) -> District:
    defaults: dict[str, Any] = dict(
        state_id=state.id, name="Sampleburg", code="SB", slug="sampleburg"
    )
    defaults.update(overrides)
    district = District(**defaults)
    session.add(district)
    session.flush()
    return district


def make_source(session: Session, **overrides: Any) -> Source:
    defaults: dict[str, Any] = dict(
        url="https://example-test.invalid/notice/schemes",
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


def make_department(
    session: Session, state: State, organization: Organization | None = None, **overrides: Any
) -> Department:
    defaults: dict[str, Any] = dict(
        name="Test Department — Not Real",
        organization_id=organization.id if organization else None,
        state_id=state.id,
    )
    defaults.update(overrides)
    department = Department(**defaults)
    session.add(department)
    session.flush()
    return department


def make_service(
    session: Session,
    *,
    organization: Organization,
    source: Source,
    state: State | None = None,
    department: Department | None = None,
    district: District | None = None,
    **overrides: Any,
) -> Service:
    """A minimal Service, for exercising `SchemeRelatedService` without
    depending on `tests/test_services/_helpers.py` — kept deliberately
    small since Schemes tests only ever need a service to link to, never
    to exercise Service's own fields."""
    defaults: dict[str, Any] = dict(
        slug=f"test-service-{uuid.uuid4().hex[:8]}",
        locale="en",
        name="Test Income Certificate Issuance (Fixture)",
        short_description="A fictional service used only to exercise the Scheme<->Service link.",
        organization_id=organization.id,
        department_id=department.id if department else None,
        category=ServiceCategory.CERTIFICATES,
        delivery_mode=DeliveryMode.BOTH,
        state_id=state.id if state else None,
        district_id=district.id if district else None,
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


def make_scheme(
    session: Session,
    *,
    organization: Organization,
    source: Source,
    state: State | None = None,
    department: Department | None = None,
    district: District | None = None,
    **overrides: Any,
) -> Scheme:
    defaults: dict[str, Any] = dict(
        slug=f"test-scheme-{uuid.uuid4().hex[:8]}",
        locale="en",
        name="Test Old-Age Pension Scheme (Fixture)",
        short_description="A fictional scheme used only to exercise the schemes domain.",
        description=None,
        organization_id=organization.id,
        department_id=department.id if department else None,
        category=SchemeCategory.PENSION,
        target_audience=None,
        state_id=state.id if state else None,
        district_id=district.id if district else None,
        official_scheme_url=None,
        application_url=None,
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


def make_benefit(session: Session, scheme: Scheme, **overrides: Any) -> SchemeBenefit:
    defaults: dict[str, Any] = dict(
        scheme_id=scheme.id,
        benefit_type=BenefitType.CASH_TRANSFER,
        description="Monthly pension amount (fictional fixture — no real figure implied).",
        amount_summary=None,
        frequency_summary="Monthly",
    )
    defaults.update(overrides)
    benefit = SchemeBenefit(**defaults)
    session.add(benefit)
    session.flush()
    return benefit


def make_requirement(session: Session, scheme: Scheme, **overrides: Any) -> SchemeRequirement:
    defaults: dict[str, Any] = dict(
        scheme_id=scheme.id,
        requirement_type=RequirementType.AGE,
        description="Applicant must be at least 60 years old (fictional fixture).",
        min_value=60,
        max_value=None,
    )
    defaults.update(overrides)
    requirement = SchemeRequirement(**defaults)
    session.add(requirement)
    session.flush()
    return requirement


def make_required_document(
    session: Session, scheme: Scheme, **overrides: Any
) -> SchemeRequiredDocument:
    defaults: dict[str, Any] = dict(
        scheme_id=scheme.id,
        name="Aadhaar Card (Fixture)",
        description=None,
        is_mandatory=True,
    )
    defaults.update(overrides)
    document = SchemeRequiredDocument(**defaults)
    session.add(document)
    session.flush()
    return document


def make_application_method(
    session: Session, scheme: Scheme, **overrides: Any
) -> SchemeApplicationMethod:
    defaults: dict[str, Any] = dict(
        scheme_id=scheme.id,
        channel_type=ApplicationChannelType.ONLINE,
        url="https://example-test.invalid/apply/test-scheme",
        instructions=None,
    )
    defaults.update(overrides)
    method = SchemeApplicationMethod(**defaults)
    session.add(method)
    session.flush()
    return method


def make_related_service(
    session: Session, scheme: Scheme, service: Service, **overrides: Any
) -> SchemeRelatedService:
    defaults: dict[str, Any] = dict(
        scheme_id=scheme.id,
        service_id=service.id,
        note=None,
    )
    defaults.update(overrides)
    related = SchemeRelatedService(**defaults)
    session.add(related)
    session.flush()
    return related
