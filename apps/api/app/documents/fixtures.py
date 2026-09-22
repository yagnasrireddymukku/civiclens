"""Synthetic Documents & Certificates fixtures — for local development
and automated tests only. Never real government data
(docs/DATA_GOVERNANCE.md §7, this phase's §25).

Naming follows docs/TESTING.md §15 exactly: fake state code "ZZ"/state
name "Testland" (the same canonical fictional geography every other
domain's fixtures share), the same "Test Recruitment Board — Not Real"
organization Jobs'/Services'/Schemes' fixtures create (get-or-create,
for the same reason state/district are — see below), `.invalid` source
URLs, "(Fixture)"/"Not Real" markers throughout. `load_fixtures` refuses
to run outside local/test environments — the same second line of
defense every other domain's fixtures use.

Two documents, exercising every feature this phase adds:

- "Test Residence Certificate (Fixture)" — simple, no dependencies.
- "Test Income Certificate (Fixture)" — has a `service_id` ("obtained
  through" a small get-or-create linked `Service`), a supporting
  document that links back to the Residence Certificate `CivicDocument`
  (§11's recursive case), requirements, and application methods.

Both the linked `Service` and a small linked `Scheme` are their own
get-or-create fixtures here — not a hard dependency on
`app.services.fixtures`/`app.schemes.fixtures` having already run — so
this module stays independently runnable, the same way every other
domain's fixtures are. The linked `Scheme` carries one
`SchemeRequiredDocument` row pointing its `civic_document_id` at the
Income Certificate, so `get_required_by()` has something real to find
— this phase's §14/§22 "where this document may be required" feature,
demonstrated end to end by fixture data alone.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.documents.enums import DocumentCategory, DocumentPublicationStatus, DocumentType
from app.documents.models import (
    CivicDocument,
    DocumentApplicationMethod,
    DocumentRequirement,
    DocumentSupportingDocument,
)
from app.documents.service import sync_document_search_index
from app.geography.enums import StateStatus
from app.geography.models import District, State
from app.institutions.enums import OrganizationType
from app.institutions.models import Department, Organization
from app.requirements.enums import ApplicationChannelType, DeliveryMode, RequirementType
from app.schemes.enums import SchemeCategory, SchemePublicationStatus
from app.schemes.models import Scheme, SchemeRequiredDocument
from app.services.enums import ServiceCategory, ServicePublicationStatus
from app.services.models import Service
from app.sources.enums import VerificationStatus
from app.sources.models import Source

_ALLOWED_ENVIRONMENTS = ("local", "test")


def _fixture_state(session: Session) -> State:
    # get-or-create: docs/TESTING.md §15's "ZZ"/"Testland" is the one
    # canonical fictional state every domain's fixtures share.
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
        url=f"https://example-test.invalid/notice/documents-fixtures-{slug_suffix}",
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
    # documents-fixtures-only load still needs a service to demonstrate
    # the "obtained through" relationship, and re-running this loader
    # must not insert a second row.
    existing = (
        session.query(Service).filter_by(slug="test-civiclens-linked-service-002").one_or_none()
    )
    if existing is not None:
        return existing

    source = _fixture_source("linked-service")
    session.add(source)
    session.flush()

    service = Service(
        slug="test-civiclens-linked-service-002",
        locale="en",
        name="Test Income Certificate Issuance Service (Fixture)",
        short_description=(
            "A fictional government service used only to exercise the Document<->Service link."
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
    return service


def _fixture_linked_scheme(
    session: Session,
    *,
    organization: Organization,
    department: Department,
    state: State,
    district: District,
) -> Scheme:
    # get-or-create, same reasoning as the linked service — a small
    # scheme existing only to carry one `SchemeRequiredDocument` row
    # that points back at a `CivicDocument`, demonstrating this phase's
    # §14/§22 "required by" reverse relationship with real fixture data.
    existing = session.query(Scheme).filter_by(slug="test-civiclens-scheme-004").one_or_none()
    if existing is not None:
        return existing

    source = _fixture_source("linked-scheme")
    session.add(source)
    session.flush()

    scheme = Scheme(
        slug="test-civiclens-scheme-004",
        locale="en",
        name="Test Family Welfare Assistance Scheme (Fixture)",
        short_description=(
            "A fictional scheme used only to exercise the Document<->Scheme "
            "'required by' relationship."
        ),
        organization_id=organization.id,
        department_id=department.id,
        category=SchemeCategory.SOCIAL_WELFARE,
        state_id=state.id,
        district_id=district.id,
        status="active",
        publication_status=SchemePublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    session.add(scheme)
    session.flush()
    return scheme


def _build_residence_certificate(
    session: Session,
    *,
    organization: Organization,
    department: Department,
    state: State,
    district: District,
) -> CivicDocument:
    source = _fixture_source("residence-certificate")
    session.add(source)
    session.flush()

    document = CivicDocument(
        slug="test-civiclens-document-001",
        locale="en",
        name="Test Residence Certificate (Fixture)",
        short_description=("A fictional certificate used only to exercise the documents domain."),
        description=(
            "This is a synthetic fixture (docs/DATA_GOVERNANCE.md §7) — not a real government "
            "certificate. It exists only to exercise the CivicLens Documents domain end to end."
        ),
        document_type=DocumentType.CERTIFICATE,
        category=DocumentCategory.RESIDENCE,
        purpose=(
            "Used to establish officially recognized residence status within Testland "
            "(fictional fixture)."
        ),
        organization_id=organization.id,
        department_id=department.id,
        delivery_mode=DeliveryMode.OFFLINE,
        state_id=state.id,
        district_id=district.id,
        official_document_url="https://example-test.invalid/documents/test-civiclens-document-001",
        application_url="https://example-test.invalid/apply/test-civiclens-document-001",
        fee_summary="Free of cost (fictional fixture).",
        processing_time_summary="5-7 working days (fictional fixture).",
        validity_summary="Valid indefinitely unless circumstances change (fictional fixture).",
        renewal_summary=None,
        status="available",
        publication_status=DocumentPublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    session.add(document)
    session.flush()

    session.add(
        DocumentApplicationMethod(
            document_id=document.id,
            channel_type=ApplicationChannelType.SERVICE_CENTER,
            url=None,
            instructions="Visit any Test Mee Seva Center — Not Real with required documents.",
        )
    )
    return document


def _build_income_certificate(
    session: Session,
    *,
    organization: Organization,
    department: Department,
    state: State,
    district: District,
    linked_service: Service,
    residence_certificate: CivicDocument,
) -> CivicDocument:
    source = _fixture_source("income-certificate")
    session.add(source)
    session.flush()

    document = CivicDocument(
        slug="test-civiclens-document-002",
        locale="en",
        name="Test Income Certificate (Fixture)",
        short_description=("A fictional certificate used only to exercise the documents domain."),
        description=(
            "This is a synthetic fixture (docs/DATA_GOVERNANCE.md §7) — not a real government "
            "certificate. It exists only to exercise the CivicLens Documents domain end to end, "
            "including its relationship to a Service and to another CivicDocument."
        ),
        document_type=DocumentType.CERTIFICATE,
        category=DocumentCategory.INCOME,
        purpose=(
            "Used to establish officially recognized income status within Testland "
            "(fictional fixture)."
        ),
        organization_id=organization.id,
        department_id=department.id,
        delivery_mode=DeliveryMode.BOTH,
        state_id=state.id,
        district_id=district.id,
        official_document_url="https://example-test.invalid/documents/test-civiclens-document-002",
        application_url="https://example-test.invalid/apply/test-civiclens-document-002",
        fee_summary="Free of cost (fictional fixture).",
        processing_time_summary="7-10 working days (fictional fixture).",
        validity_summary="Valid for 6 months from the date of issue (fictional fixture).",
        renewal_summary="Reapply after expiry — no separate renewal process (fictional fixture).",
        service_id=linked_service.id,
        status="available",
        publication_status=DocumentPublicationStatus.PUBLISHED,
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    session.add(document)
    session.flush()

    session.add_all(
        [
            DocumentRequirement(
                document_id=document.id,
                requirement_type=RequirementType.RESIDENCY,
                description="Applicant must be a resident of Testland (fictional fixture).",
                min_value=None,
                max_value=None,
            ),
            DocumentRequirement(
                document_id=document.id,
                requirement_type=RequirementType.AGE,
                description="Applicant must be at least 18 years old (fictional fixture).",
                min_value=18,
                max_value=None,
            ),
        ]
    )
    session.add_all(
        [
            DocumentSupportingDocument(
                document_id=document.id,
                name="Aadhaar Card (Fixture)",
                description="Proof of identity — fictional fixture, not a real requirement.",
                is_mandatory=True,
                civic_document_id=None,
            ),
            # The recursive case (this phase's §11): a supporting
            # document that is itself a modeled `CivicDocument`.
            DocumentSupportingDocument(
                document_id=document.id,
                name="Residence Certificate (Fixture)",
                description="Proof of residence — fictional fixture, not a real requirement.",
                is_mandatory=True,
                civic_document_id=residence_certificate.id,
            ),
        ]
    )
    session.add(
        DocumentApplicationMethod(
            document_id=document.id,
            channel_type=ApplicationChannelType.ONLINE,
            url="https://example-test.invalid/apply/test-civiclens-document-002",
            instructions=None,
        )
    )
    return document


def load_fixtures(session: Session) -> None:
    """Inserts two small, fixed, clearly-fictional documents — a
    Residence Certificate and an Income Certificate (the latter linked
    to a Service and, for one of its supporting documents, back to the
    former) — plus a small linked Scheme carrying a
    `SchemeRequiredDocument` that points at the Income Certificate, then
    indexes both documents into Civic Search, exercising the full
    CivicDocument -> search_documents pipeline and the "required by"
    reverse relationship end to end. Refuses to run unless `APP_ENV` is
    "local" or "test" — see module docstring.
    """
    settings = get_settings()
    if settings.app_env not in _ALLOWED_ENVIRONMENTS:
        raise RuntimeError(
            f"Refusing to load document fixtures: APP_ENV={settings.app_env!r} is not one of "
            f"{_ALLOWED_ENVIRONMENTS}. Fixtures must never reach a staging/production database."
        )

    state = _fixture_state(session)
    district = _fixture_district(session, state)
    organization = _fixture_organization(session, state)
    department = _fixture_department(session, state, organization)
    linked_service = _fixture_linked_service(
        session, organization=organization, department=department, state=state, district=district
    )
    linked_scheme = _fixture_linked_scheme(
        session, organization=organization, department=department, state=state, district=district
    )

    residence_certificate = _build_residence_certificate(
        session, organization=organization, department=department, state=state, district=district
    )
    income_certificate = _build_income_certificate(
        session,
        organization=organization,
        department=department,
        state=state,
        district=district,
        linked_service=linked_service,
        residence_certificate=residence_certificate,
    )

    # get-or-create: re-running this loader must not insert a duplicate
    # requirement row on the shared linked scheme.
    existing_required_document = (
        session.query(SchemeRequiredDocument)
        .filter_by(scheme_id=linked_scheme.id, civic_document_id=income_certificate.id)
        .one_or_none()
    )
    if existing_required_document is None:
        session.add(
            SchemeRequiredDocument(
                scheme_id=linked_scheme.id,
                name="Income Certificate (Fixture)",
                description="Proof of household income — fictional fixture.",
                is_mandatory=True,
                civic_document_id=income_certificate.id,
            )
        )

    for document in (residence_certificate, income_certificate):
        sync_document_search_index(session, document)
    session.commit()
