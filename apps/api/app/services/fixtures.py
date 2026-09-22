"""Synthetic Service fixtures — for local development and automated
tests only. Never real government data (docs/DATA_GOVERNANCE.md §7, this
phase's §22).

Naming follows docs/TESTING.md §15 / this phase's §22 exactly: fake
state code "ZZ"/state name "Testland" (the same canonical fictional
geography `app.search.fixtures`/`app.jobs.fixtures` share), the same
"Test Recruitment Board — Not Real" organization Jobs' fixtures create
(get-or-create, for the same reason state/district are — see below),
`.invalid` source URLs, "(Fixture)"/"Not Real" markers throughout.
`load_fixtures` refuses to run outside local/test environments — the
same second line of defense every other domain's fixtures use.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.geography.enums import StateStatus
from app.geography.models import District, State
from app.institutions.enums import OrganizationType
from app.institutions.models import Department, Organization
from app.requirements.enums import ApplicationChannelType, RequirementType
from app.services.enums import DeliveryMode, ServiceCategory, ServicePublicationStatus
from app.services.models import ApplicationMethod, RequiredDocument, Service, ServiceRequirement
from app.services.service import sync_service_search_index
from app.sources.enums import VerificationStatus
from app.sources.models import Source

_ALLOWED_ENVIRONMENTS = ("local", "test")


def _fixture_state(session: Session) -> State:
    # get-or-create: docs/TESTING.md §15's "ZZ"/"Testland" is the one
    # canonical fictional state every domain's fixtures share — see
    # app/search/fixtures.py and app/jobs/fixtures.py's matching fix for
    # the duplicate-state-code collision this avoids.
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
    # get-or-create, same reasoning as state/district: `organizations.name`
    # is globally unique, and this is the same fictional board Jobs'
    # fixtures create — seeding both without get-or-create would collide
    # exactly like the state-code bug did.
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


def _fixture_source() -> Source:
    return Source(
        url="https://example-test.invalid/notice/services-fixtures",
        title="Test Notice — Not Real",
        organization="Test Recruitment Board — Not Real",
        source_type="test-fixture",
        retrieved_date=datetime.date(2026, 1, 1),
    )


def load_fixtures(session: Session) -> None:
    """Inserts one small, fixed, clearly-fictional service with its
    requirements/documents/application methods, then indexes it into
    Civic Search — exercising the full Service -> search_documents
    pipeline end to end. Refuses to run unless `APP_ENV` is "local" or
    "test" — see module docstring.
    """
    settings = get_settings()
    if settings.app_env not in _ALLOWED_ENVIRONMENTS:
        raise RuntimeError(
            f"Refusing to load service fixtures: APP_ENV={settings.app_env!r} is not one of "
            f"{_ALLOWED_ENVIRONMENTS}. Fixtures must never reach a staging/production database."
        )

    state = _fixture_state(session)
    district = _fixture_district(session, state)
    organization = _fixture_organization(session, state)
    department = _fixture_department(session, state, organization)

    source = _fixture_source()
    session.add(source)
    session.flush()

    last_verified_at = datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC)

    service = Service(
        slug="test-civiclens-service-001",
        locale="en",
        name="Test Income Certificate Issuance (Fixture)",
        short_description=(
            "A fictional government service used only to exercise the services domain."
        ),
        description=(
            "This is a synthetic fixture (docs/DATA_GOVERNANCE.md §7) — not a real government "
            "service. It exists only to exercise the CivicLens Services domain end to end."
        ),
        organization_id=organization.id,
        department_id=department.id,
        category=ServiceCategory.CERTIFICATES,
        service_type="certificate issuance",
        target_audience="Residents of Testland requiring proof of income (fictional fixture).",
        delivery_mode=DeliveryMode.BOTH,
        state_id=state.id,
        district_id=district.id,
        official_service_url="https://example-test.invalid/services/test-civiclens-service-001",
        application_url="https://example-test.invalid/apply/test-civiclens-service-001",
        fee_summary="Free of cost (fictional fixture).",
        processing_time_summary="7-10 working days (fictional fixture).",
        location_summary="Available at Test Mee Seva Center — Not Real, Sampleburg.",
        status="available",
        publication_status=ServicePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=last_verified_at,
    )
    session.add(service)
    session.flush()

    session.add_all(
        [
            ServiceRequirement(
                service_id=service.id,
                requirement_type=RequirementType.AGE,
                description="Applicant must be at least 18 years old (fictional fixture).",
                min_value=18,
                max_value=None,
            ),
            ServiceRequirement(
                service_id=service.id,
                requirement_type=RequirementType.RESIDENCY,
                description="Applicant must be a resident of Testland (fictional fixture).",
                min_value=None,
                max_value=None,
            ),
        ]
    )

    session.add_all(
        [
            RequiredDocument(
                service_id=service.id,
                name="Aadhaar Card (Fixture)",
                description="Proof of identity — fictional fixture, not a real requirement.",
                is_mandatory=True,
            ),
            RequiredDocument(
                service_id=service.id,
                name="Residence Proof (Fixture)",
                description=None,
                is_mandatory=True,
            ),
            RequiredDocument(
                service_id=service.id,
                name="Passport-size Photograph (Fixture)",
                description=None,
                is_mandatory=False,
            ),
        ]
    )

    session.add_all(
        [
            ApplicationMethod(
                service_id=service.id,
                channel_type=ApplicationChannelType.ONLINE,
                url="https://example-test.invalid/apply/test-civiclens-service-001",
                instructions=None,
            ),
            ApplicationMethod(
                service_id=service.id,
                channel_type=ApplicationChannelType.SERVICE_CENTER,
                url=None,
                instructions="Visit any Test Mee Seva Center — Not Real with required documents.",
            ),
        ]
    )

    sync_service_search_index(session, service)
    session.commit()
