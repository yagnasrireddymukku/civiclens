"""Documents domain model/relationship/constraint tests. Fixture data is
unambiguously fictional (docs/DATA_GOVERNANCE.md §7, docs/TESTING.md §15).
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.documents.models import (
    CivicDocument,
    DocumentApplicationMethod,
    DocumentRequirement,
    DocumentSupportingDocument,
)
from tests.test_documents._helpers import (
    make_application_method,
    make_department,
    make_district,
    make_document,
    make_organization,
    make_requirement,
    make_scheme,
    make_scheme_required_document,
    make_service,
    make_service_required_document,
    make_source,
    make_state,
    make_supporting_document,
)


def test_document_relationships_and_child_rows(db_session: Session) -> None:
    state = make_state(db_session)
    district = make_district(db_session, state)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    department = make_department(db_session, state, organization=organization)
    linked_service = make_service(db_session, organization=organization, source=source)
    document = make_document(
        db_session,
        organization=organization,
        source=source,
        state=state,
        department=department,
        district=district,
        service_id=linked_service.id,
    )
    requirement = make_requirement(db_session, document)
    supporting = make_supporting_document(db_session, document)
    method = make_application_method(db_session, document)

    db_session.refresh(organization)
    db_session.refresh(document)

    assert document in organization.civic_documents
    assert document.department is department
    assert document.organization is organization
    assert document.service is linked_service
    assert requirement in document.requirements
    assert requirement.document is document
    assert supporting in document.supporting_documents
    assert method in document.application_methods


def test_document_requires_an_existing_organization(db_session: Session) -> None:
    source = make_source(db_session)

    db_session.add(
        CivicDocument(
            slug="orphan-document",
            locale="en",
            name="Orphan Document",
            organization_id=uuid.uuid4(),
            document_type="CERTIFICATE",
            category="INCOME",
            delivery_mode="BOTH",
            publication_status="DRAFT",
            source_id=source.id,
            verification_status="UNVERIFIED",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_document_cannot_be_created_without_a_source(db_session: Session) -> None:
    """Mirrors the literal Phase 6 acceptance criterion, applied to
    Documents: a document cannot be created without a `source_id`."""
    state = make_state(db_session)
    organization = make_organization(db_session, state)

    with pytest.raises(IntegrityError):
        db_session.add(
            CivicDocument(
                slug="sourceless-document",
                locale="en",
                name="Sourceless Document",
                organization_id=organization.id,
                document_type="CERTIFICATE",
                category="INCOME",
                delivery_mode="BOTH",
                publication_status="DRAFT",
                source_id=None,  # type: ignore[arg-type]
                verification_status="UNVERIFIED",
            )
        )
        db_session.flush()


def test_document_slug_must_be_unique(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_document(db_session, organization=organization, source=source, slug="dup-slug")

    with pytest.raises(IntegrityError):
        make_document(db_session, organization=organization, source=source, slug="dup-slug")


def test_document_state_and_district_are_nullable(db_session: Session) -> None:
    """Like Service/Scheme, a document may be available statewide/
    nationally rather than scoped to one state."""
    source = make_source(db_session)
    state = make_state(db_session)
    organization = make_organization(db_session, state)

    document = make_document(
        db_session, organization=organization, source=source, state=None, district=None
    )

    assert document.state_id is None
    assert document.district_id is None


def test_document_service_id_is_nullable(db_session: Session) -> None:
    """This phase's §13: "do not require every document to have a
    Service" — the "obtained through" relationship is optional."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)

    document = make_document(db_session, organization=organization, source=source)

    assert document.service_id is None
    assert document.service is None


def test_deleting_organization_is_restricted_while_documents_reference_it(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_document(db_session, organization=organization, source=source)

    db_session.delete(organization)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_department_sets_document_department_to_null(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    department = make_department(db_session, state, organization=organization)
    document = make_document(
        db_session, organization=organization, source=source, department=department
    )
    document_id = document.id

    db_session.delete(department)
    db_session.flush()

    db_session.expire_all()
    reloaded = db_session.get(CivicDocument, document_id)
    assert reloaded is not None
    assert reloaded.department_id is None


def test_deleting_linked_service_sets_document_service_id_to_null(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    linked_service = make_service(db_session, organization=organization, source=source)
    document = make_document(
        db_session, organization=organization, source=source, service_id=linked_service.id
    )
    document_id = document.id

    db_session.delete(linked_service)
    db_session.flush()

    db_session.expire_all()
    reloaded = db_session.get(CivicDocument, document_id)
    assert reloaded is not None
    assert reloaded.service_id is None


def test_deleting_document_cascades_to_children(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)
    requirement = make_requirement(db_session, document)
    supporting = make_supporting_document(db_session, document)
    method = make_application_method(db_session, document)
    requirement_id, supporting_id, method_id = requirement.id, supporting.id, method.id

    db_session.delete(document)
    db_session.flush()

    assert db_session.get(DocumentRequirement, requirement_id) is None
    assert db_session.get(DocumentSupportingDocument, supporting_id) is None
    assert db_session.get(DocumentApplicationMethod, method_id) is None


def test_deleting_referenced_civic_document_sets_supporting_document_link_to_null(
    db_session: Session,
) -> None:
    """The recursive case (this phase's §11): deleting the *referenced*
    `CivicDocument` must not delete the supporting-document row on the
    *referencing* document — only clear the link."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    referenced = make_document(db_session, organization=organization, source=source)
    referencing = make_document(db_session, organization=organization, source=source)
    supporting = make_supporting_document(db_session, referencing, civic_document_id=referenced.id)
    supporting_id, referencing_id = supporting.id, referencing.id

    db_session.delete(referenced)
    db_session.flush()

    db_session.expire_all()
    reloaded = db_session.get(DocumentSupportingDocument, supporting_id)
    assert reloaded is not None
    assert reloaded.civic_document_id is None
    assert db_session.get(CivicDocument, referencing_id) is not None


def test_document_soft_delete_field_defaults_to_none(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)

    assert document.deleted_at is None


def test_service_required_document_civic_document_id_links_to_document(
    db_session: Session,
) -> None:
    """The additive Phase 10 column on an already-shipped Services
    table (this phase's §14/§22)."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)
    service = make_service(db_session, organization=organization, source=source)
    required = make_service_required_document(db_session, service, civic_document_id=document.id)

    db_session.refresh(required)

    assert required.civic_document_id == document.id
    assert required.civic_document is document


def test_scheme_required_document_civic_document_id_links_to_document(
    db_session: Session,
) -> None:
    """The additive Phase 10 column on an already-shipped Schemes
    table (this phase's §14/§22) — covers Scholarships transparently,
    since a scholarship is a Scheme (Phase 9)."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)
    scheme = make_scheme(db_session, organization=organization, source=source)
    required = make_scheme_required_document(db_session, scheme, civic_document_id=document.id)

    db_session.refresh(required)

    assert required.civic_document_id == document.id
    assert required.civic_document is document


def test_deleting_document_sets_required_document_links_to_null(db_session: Session) -> None:
    """Deleting the `CivicDocument` a requirement points at must not
    delete the requirement row itself — only clear the link (`ON DELETE
    SET NULL`, not `CASCADE`, on the referencing side)."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)
    service = make_service(db_session, organization=organization, source=source)
    required = make_service_required_document(db_session, service, civic_document_id=document.id)
    required_id = required.id

    db_session.delete(document)
    db_session.flush()

    db_session.expire_all()
    reloaded = db_session.get(type(required), required_id)
    assert reloaded is not None
    assert reloaded.civic_document_id is None
