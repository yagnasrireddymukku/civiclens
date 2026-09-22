"""Synthetic Scheme fixtures — for local development and automated
tests only. Never real government data (docs/DATA_GOVERNANCE.md §7, this
phase's §25).

Naming follows docs/TESTING.md §15 / this phase's §25 exactly: fake
state code "ZZ"/state name "Testland" (the same canonical fictional
geography every other domain's fixtures share), the same "Test
Recruitment Board — Not Real" organization Jobs'/Services' fixtures
create (get-or-create, for the same reason state/district are — see
below), `.invalid` source URLs, "(Fixture)"/"Not Real" markers
throughout. `load_fixtures` refuses to run outside local/test
environments — the same second line of defense every other domain's
fixtures use.

Three schemes, per this phase's §25 suggestion: one financial-benefit
scheme (a cash pension), one scholarship-like scheme, and one scheme
linked to a service via `SchemeRelatedService`. The linked service is
its own small get-or-create fixture here — not a hard dependency on
`app.services.fixtures` having already run — so this module stays
independently runnable, the same way every other domain's fixtures are.

The scholarship-like scheme (Phase 9) additionally carries a
`ScholarshipDetail` row exercising every field of that extension table —
education level, study mode, structured academic-performance thresholds,
an application window, and a renewal note — all clearly fictional
figures/dates, never presented as real.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.geography.enums import StateStatus
from app.geography.models import District, State
from app.institutions.enums import OrganizationType
from app.institutions.models import Department, Organization
from app.requirements.enums import ApplicationChannelType, DeliveryMode, RequirementType
from app.schemes.enums import (
    BenefitType,
    EducationLevel,
    SchemeCategory,
    SchemePublicationStatus,
    StudyMode,
)
from app.schemes.models import (
    Scheme,
    SchemeApplicationMethod,
    SchemeBenefit,
    SchemeRelatedService,
    SchemeRequiredDocument,
    SchemeRequirement,
    ScholarshipDetail,
)
from app.schemes.service import sync_scheme_search_index
from app.services.enums import ServiceCategory, ServicePublicationStatus
from app.services.models import Service
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
    # is globally unique, and this is the same fictional board Jobs'/
    # Services' fixtures create — seeding all three without get-or-create
    # would collide exactly like the state-code bug did.
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
        url=f"https://example-test.invalid/notice/schemes-fixtures-{slug_suffix}",
        title="Test Notice — Not Real",
        organization="Test Recruitment Board — Not Real",
        source_type="test-fixture",
        retrieved_date=datetime.date(2026, 1, 1),
    )


def _fixture_linked_service(
    session: Session,
    *,
    organization: Organization,
    department: Department,
    state: State,
    district: District,
) -> Service:
    # get-or-create, same reasoning as state/organization/department: a
    # scheme-fixtures-only load (without `app.services.fixtures` having
    # run first) still needs a service to link the service-linked scheme
    # to, and re-running this loader must not insert a second row.
    existing = (
        session.query(Service).filter_by(slug="test-civiclens-linked-service-001").one_or_none()
    )
    if existing is not None:
        return existing

    source = _fixture_source("linked-service")
    session.add(source)
    session.flush()

    service = Service(
        slug="test-civiclens-linked-service-001",
        locale="en",
        name="Test Income Certificate Issuance for Scheme Linking (Fixture)",
        short_description=(
            "A fictional government service used only to exercise the Scheme<->Service link."
        ),
        organization_id=organization.id,
        department_id=department.id,
        category=ServiceCategory.CERTIFICATES,
        service_type="certificate issuance",
        delivery_mode=DeliveryMode.BOTH,
        state_id=state.id,
        district_id=district.id,
        status="available",
        publication_status=ServicePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    session.add(service)
    session.flush()
    sync_service_search_index(session, service)
    return service


def _build_pension_scheme(
    session: Session,
    *,
    organization: Organization,
    department: Department,
    state: State,
    district: District,
) -> Scheme:
    source = _fixture_source("pension")
    session.add(source)
    session.flush()

    scheme = Scheme(
        slug="test-civiclens-scheme-001",
        locale="en",
        name="Test Old-Age Pension Scheme (Fixture)",
        short_description=(
            "A fictional government pension scheme used only to exercise the schemes domain."
        ),
        description=(
            "This is a synthetic fixture (docs/DATA_GOVERNANCE.md §7) — not a real government "
            "scheme. It exists only to exercise the CivicLens Schemes domain end to end."
        ),
        organization_id=organization.id,
        department_id=department.id,
        category=SchemeCategory.PENSION,
        target_audience="Residents of Testland aged 60 and above (fictional fixture).",
        state_id=state.id,
        district_id=district.id,
        official_scheme_url="https://example-test.invalid/schemes/test-civiclens-scheme-001",
        application_url="https://example-test.invalid/apply/test-civiclens-scheme-001",
        status="active",
        publication_status=SchemePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    session.add(scheme)
    session.flush()

    session.add(
        SchemeBenefit(
            scheme_id=scheme.id,
            benefit_type=BenefitType.CASH_TRANSFER,
            description="Monthly pension amount (fictional fixture — no real figure implied).",
            amount_summary="Fictional fixture amount — not a real figure.",
            frequency_summary="Monthly",
        )
    )
    session.add_all(
        [
            SchemeRequirement(
                scheme_id=scheme.id,
                requirement_type=RequirementType.AGE,
                description="Applicant must be at least 60 years old (fictional fixture).",
                min_value=60,
                max_value=None,
            ),
            SchemeRequirement(
                scheme_id=scheme.id,
                requirement_type=RequirementType.RESIDENCY,
                description="Applicant must be a resident of Testland (fictional fixture).",
                min_value=None,
                max_value=None,
            ),
        ]
    )
    session.add(
        SchemeRequiredDocument(
            scheme_id=scheme.id,
            name="Aadhaar Card (Fixture)",
            description="Proof of identity — fictional fixture, not a real requirement.",
            is_mandatory=True,
        )
    )
    session.add(
        SchemeApplicationMethod(
            scheme_id=scheme.id,
            channel_type=ApplicationChannelType.SERVICE_CENTER,
            url=None,
            instructions="Visit any Test Mee Seva Center — Not Real with required documents.",
        )
    )
    return scheme


def _build_scholarship_scheme(
    session: Session,
    *,
    organization: Organization,
    department: Department,
    state: State,
    district: District,
) -> Scheme:
    source = _fixture_source("scholarship")
    session.add(source)
    session.flush()

    scheme = Scheme(
        slug="test-civiclens-scheme-002",
        locale="en",
        name="Test Merit Scholarship Scheme (Fixture)",
        short_description=(
            "A fictional government scholarship scheme used only to exercise the schemes domain."
        ),
        description=(
            "This is a synthetic fixture (docs/DATA_GOVERNANCE.md §7) — not a real government "
            "scholarship. It exists only to exercise the CivicLens Schemes domain end to end."
        ),
        organization_id=organization.id,
        department_id=department.id,
        category=SchemeCategory.SCHOLARSHIP,
        target_audience=(
            "Students of Testland enrolled in a recognized institution (fictional fixture)."
        ),
        state_id=state.id,
        district_id=district.id,
        official_scheme_url="https://example-test.invalid/schemes/test-civiclens-scheme-002",
        application_url="https://example-test.invalid/apply/test-civiclens-scheme-002",
        status="active",
        publication_status=SchemePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    session.add(scheme)
    session.flush()

    session.add(
        SchemeBenefit(
            scheme_id=scheme.id,
            benefit_type=BenefitType.SCHOLARSHIP_AMOUNT,
            description="One-time scholarship amount (fictional fixture — no real figure implied).",
            amount_summary="Fictional fixture amount — not a real figure.",
            frequency_summary="Annual",
        )
    )
    session.add(
        SchemeRequirement(
            scheme_id=scheme.id,
            requirement_type=RequirementType.OTHER,
            description=(
                "Applicant must be enrolled as a student in good academic standing "
                "(fictional fixture — represented as OTHER rather than a dedicated "
                "'student status' enum value, per docs/DATABASE.md §11)."
            ),
            min_value=None,
            max_value=None,
        )
    )
    session.add(
        SchemeRequiredDocument(
            scheme_id=scheme.id,
            name="Bonafide Student Certificate (Fixture)",
            description="Proof of current enrollment — fictional fixture, not a real requirement.",
            is_mandatory=True,
        )
    )
    session.add(
        SchemeApplicationMethod(
            scheme_id=scheme.id,
            channel_type=ApplicationChannelType.ONLINE,
            url="https://example-test.invalid/apply/test-civiclens-scheme-002",
            instructions=None,
        )
    )
    session.add(
        ScholarshipDetail(
            scheme_id=scheme.id,
            education_level=EducationLevel.UNDERGRADUATE,
            course_discipline="Any UGC-recognized undergraduate discipline (fictional fixture).",
            institution_type="Government or government-aided colleges (fictional fixture).",
            study_mode=StudyMode.FULL_TIME,
            year_of_study="Any year of study (fictional fixture).",
            minimum_percentage=Decimal("60.00"),
            minimum_cgpa=None,
            academic_requirement_notes=(
                "Must not hold another active scholarship for the same academic year "
                "(fictional fixture)."
            ),
            application_opens=datetime.date(2026, 6, 1),
            application_closes=datetime.date(2026, 7, 31),
            correction_window_end=datetime.date(2026, 8, 7),
            academic_year="2026-27",
            renewable=True,
            renewal_notes=(
                "Renewable each academic year subject to continued enrollment and minimum "
                "percentage (fictional fixture)."
            ),
        )
    )
    return scheme


def _build_service_linked_scheme(
    session: Session,
    *,
    organization: Organization,
    department: Department,
    state: State,
    district: District,
    linked_service: Service,
) -> Scheme:
    source = _fixture_source("income-support")
    session.add(source)
    session.flush()

    scheme = Scheme(
        slug="test-civiclens-scheme-003",
        locale="en",
        name="Test Income Support Scheme (Fixture)",
        short_description=(
            "A fictional government income-support scheme used only to exercise the "
            "Scheme<->Service relationship."
        ),
        description=(
            "This is a synthetic fixture (docs/DATA_GOVERNANCE.md §7) — not a real government "
            "scheme. It exists only to exercise the CivicLens Schemes domain end to end, "
            "including its relationship to a Service record."
        ),
        organization_id=organization.id,
        department_id=department.id,
        category=SchemeCategory.FINANCIAL_ASSISTANCE,
        target_audience="Low-income households in Testland (fictional fixture).",
        state_id=state.id,
        district_id=district.id,
        official_scheme_url="https://example-test.invalid/schemes/test-civiclens-scheme-003",
        application_url="https://example-test.invalid/apply/test-civiclens-scheme-003",
        status="active",
        publication_status=SchemePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    session.add(scheme)
    session.flush()

    session.add(
        SchemeBenefit(
            scheme_id=scheme.id,
            benefit_type=BenefitType.CASH_TRANSFER,
            description=(
                "One-time income support payment (fictional fixture — no real figure implied)."
            ),
            amount_summary="Fictional fixture amount — not a real figure.",
            frequency_summary="One-time",
        )
    )
    session.add(
        SchemeRequirement(
            scheme_id=scheme.id,
            requirement_type=RequirementType.INCOME,
            description="Household income must fall below a fictional fixture threshold.",
            min_value=None,
            max_value=None,
        )
    )
    session.add(
        SchemeRelatedService(
            scheme_id=scheme.id,
            service_id=linked_service.id,
            note=(
                "Applicants typically obtain this service's income certificate before "
                "applying for the scheme (fictional fixture)."
            ),
        )
    )
    return scheme


def load_fixtures(session: Session) -> None:
    """Inserts three small, fixed, clearly-fictional schemes — one
    financial-benefit (pension), one scholarship-like, and one linked to
    a Service — then indexes each into Civic Search, exercising the
    full Scheme -> search_documents pipeline end to end. Refuses to run
    unless `APP_ENV` is "local" or "test" — see module docstring.
    """
    settings = get_settings()
    if settings.app_env not in _ALLOWED_ENVIRONMENTS:
        raise RuntimeError(
            f"Refusing to load scheme fixtures: APP_ENV={settings.app_env!r} is not one of "
            f"{_ALLOWED_ENVIRONMENTS}. Fixtures must never reach a staging/production database."
        )

    state = _fixture_state(session)
    district = _fixture_district(session, state)
    organization = _fixture_organization(session, state)
    department = _fixture_department(session, state, organization)
    linked_service = _fixture_linked_service(
        session, organization=organization, department=department, state=state, district=district
    )

    schemes = [
        _build_pension_scheme(
            session,
            organization=organization,
            department=department,
            state=state,
            district=district,
        ),
        _build_scholarship_scheme(
            session,
            organization=organization,
            department=department,
            state=state,
            district=district,
        ),
        _build_service_linked_scheme(
            session,
            organization=organization,
            department=department,
            state=state,
            district=district,
            linked_service=linked_service,
        ),
    ]

    for scheme in schemes:
        sync_scheme_search_index(session, scheme)
    session.commit()
