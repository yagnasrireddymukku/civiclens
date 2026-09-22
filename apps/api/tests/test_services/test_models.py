"""Services domain model/relationship/constraint tests. Fixture data is
unambiguously fictional (docs/DATA_GOVERNANCE.md §7, docs/TESTING.md §15).
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.models import (
    ApplicationMethod,
    RequiredDocument,
    Service,
    ServiceRequirement,
)
from tests.test_services._helpers import (
    make_application_method,
    make_department,
    make_district,
    make_organization,
    make_required_document,
    make_requirement,
    make_service,
    make_source,
    make_state,
)


def test_service_relationships_and_child_rows(db_session: Session) -> None:
    state = make_state(db_session)
    district = make_district(db_session, state)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    department = make_department(db_session, state, organization=organization)
    service = make_service(
        db_session,
        organization=organization,
        source=source,
        state=state,
        department=department,
        district=district,
    )
    requirement = make_requirement(db_session, service)
    document = make_required_document(db_session, service)
    method = make_application_method(db_session, service)

    db_session.refresh(organization)
    db_session.refresh(service)

    assert service in organization.services
    assert service.department is department
    assert service.organization is organization
    assert requirement in service.requirements
    assert requirement.service is service
    assert document in service.required_documents
    assert method in service.application_methods


def test_service_requires_an_existing_organization(db_session: Session) -> None:
    source = make_source(db_session)

    db_session.add(
        Service(
            slug="orphan-service",
            locale="en",
            name="Orphan Service",
            organization_id=uuid.uuid4(),
            category="CERTIFICATES",
            delivery_mode="ONLINE",
            publication_status="DRAFT",
            source_id=source.id,
            verification_status="UNVERIFIED",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_service_cannot_be_created_without_a_source(db_session: Session) -> None:
    """Mirrors the literal Phase 6 acceptance criterion, applied to
    Services: a service cannot be created without a `source_id`."""
    state = make_state(db_session)
    organization = make_organization(db_session, state)

    with pytest.raises(IntegrityError):
        db_session.add(
            Service(
                slug="sourceless-service",
                locale="en",
                name="Sourceless Service",
                organization_id=organization.id,
                category="CERTIFICATES",
                delivery_mode="ONLINE",
                publication_status="DRAFT",
                source_id=None,  # type: ignore[arg-type]
                verification_status="UNVERIFIED",
            )
        )
        db_session.flush()


def test_service_slug_must_be_unique(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_service(db_session, organization=organization, source=source, slug="dup-slug")

    with pytest.raises(IntegrityError):
        make_service(db_session, organization=organization, source=source, slug="dup-slug")


def test_service_state_and_district_are_nullable(db_session: Session) -> None:
    """Unlike Job, a service may be available statewide/nationally
    rather than scoped to one state (this phase's §4.1)."""
    source = make_source(db_session)
    state = make_state(db_session)
    organization = make_organization(db_session, state)

    service = make_service(
        db_session, organization=organization, source=source, state=None, district=None
    )

    assert service.state_id is None
    assert service.district_id is None


def test_deleting_organization_is_restricted_while_services_reference_it(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_service(db_session, organization=organization, source=source)

    db_session.delete(organization)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_department_sets_service_department_to_null(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    department = make_department(db_session, state, organization=organization)
    service = make_service(
        db_session, organization=organization, source=source, department=department
    )
    service_id = service.id

    db_session.delete(department)
    db_session.flush()

    db_session.expire_all()
    reloaded_service = db_session.get(Service, service_id)
    assert reloaded_service is not None
    assert reloaded_service.department_id is None


def test_deleting_service_cascades_to_requirements_documents_and_methods(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(db_session, organization=organization, source=source)
    requirement = make_requirement(db_session, service)
    document = make_required_document(db_session, service)
    method = make_application_method(db_session, service)
    requirement_id, document_id, method_id = requirement.id, document.id, method.id

    db_session.delete(service)
    db_session.flush()

    assert db_session.get(ServiceRequirement, requirement_id) is None
    assert db_session.get(RequiredDocument, document_id) is None
    assert db_session.get(ApplicationMethod, method_id) is None


def test_service_soft_delete_field_defaults_to_none(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(db_session, organization=organization, source=source)

    assert service.deleted_at is None
