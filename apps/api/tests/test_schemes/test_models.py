"""Schemes domain model/relationship/constraint tests. Fixture data is
unambiguously fictional (docs/DATA_GOVERNANCE.md §7, docs/TESTING.md §15).
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schemes.models import (
    Scheme,
    SchemeApplicationMethod,
    SchemeBenefit,
    SchemeRelatedService,
    SchemeRequiredDocument,
    SchemeRequirement,
)
from tests.test_schemes._helpers import (
    make_application_method,
    make_benefit,
    make_department,
    make_district,
    make_organization,
    make_related_service,
    make_required_document,
    make_requirement,
    make_scheme,
    make_service,
    make_source,
    make_state,
)


def test_scheme_relationships_and_child_rows(db_session: Session) -> None:
    state = make_state(db_session)
    district = make_district(db_session, state)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    department = make_department(db_session, state, organization=organization)
    scheme = make_scheme(
        db_session,
        organization=organization,
        source=source,
        state=state,
        department=department,
        district=district,
    )
    benefit = make_benefit(db_session, scheme)
    requirement = make_requirement(db_session, scheme)
    document = make_required_document(db_session, scheme)
    method = make_application_method(db_session, scheme)
    linked_service = make_service(db_session, organization=organization, source=source)
    related = make_related_service(db_session, scheme, linked_service)

    db_session.refresh(organization)
    db_session.refresh(scheme)

    assert scheme in organization.schemes
    assert scheme.department is department
    assert scheme.organization is organization
    assert benefit in scheme.benefits
    assert requirement in scheme.requirements
    assert requirement.scheme is scheme
    assert document in scheme.required_documents
    assert method in scheme.application_methods
    assert related in scheme.related_services
    assert related.service is linked_service


def test_scheme_requires_an_existing_organization(db_session: Session) -> None:
    source = make_source(db_session)

    db_session.add(
        Scheme(
            slug="orphan-scheme",
            locale="en",
            name="Orphan Scheme",
            organization_id=uuid.uuid4(),
            category="PENSION",
            publication_status="DRAFT",
            source_id=source.id,
            verification_status="UNVERIFIED",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_scheme_cannot_be_created_without_a_source(db_session: Session) -> None:
    """Mirrors the literal Phase 6 acceptance criterion, applied to
    Schemes: a scheme cannot be created without a `source_id`."""
    state = make_state(db_session)
    organization = make_organization(db_session, state)

    with pytest.raises(IntegrityError):
        db_session.add(
            Scheme(
                slug="sourceless-scheme",
                locale="en",
                name="Sourceless Scheme",
                organization_id=organization.id,
                category="PENSION",
                publication_status="DRAFT",
                source_id=None,  # type: ignore[arg-type]
                verification_status="UNVERIFIED",
            )
        )
        db_session.flush()


def test_scheme_slug_must_be_unique(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_scheme(db_session, organization=organization, source=source, slug="dup-slug")

    with pytest.raises(IntegrityError):
        make_scheme(db_session, organization=organization, source=source, slug="dup-slug")


def test_scheme_state_and_district_are_nullable(db_session: Session) -> None:
    """Like Service (and unlike Job), a scheme may be available
    statewide/nationally rather than scoped to one state."""
    source = make_source(db_session)
    state = make_state(db_session)
    organization = make_organization(db_session, state)

    scheme = make_scheme(
        db_session, organization=organization, source=source, state=None, district=None
    )

    assert scheme.state_id is None
    assert scheme.district_id is None


def test_deleting_organization_is_restricted_while_schemes_reference_it(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_scheme(db_session, organization=organization, source=source)

    db_session.delete(organization)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_department_sets_scheme_department_to_null(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    department = make_department(db_session, state, organization=organization)
    scheme = make_scheme(
        db_session, organization=organization, source=source, department=department
    )
    scheme_id = scheme.id

    db_session.delete(department)
    db_session.flush()

    db_session.expire_all()
    reloaded_scheme = db_session.get(Scheme, scheme_id)
    assert reloaded_scheme is not None
    assert reloaded_scheme.department_id is None


def test_deleting_scheme_cascades_to_children(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)
    benefit = make_benefit(db_session, scheme)
    requirement = make_requirement(db_session, scheme)
    document = make_required_document(db_session, scheme)
    method = make_application_method(db_session, scheme)
    linked_service = make_service(db_session, organization=organization, source=source)
    related = make_related_service(db_session, scheme, linked_service)
    benefit_id, requirement_id = benefit.id, requirement.id
    document_id, method_id, related_id = document.id, method.id, related.id

    db_session.delete(scheme)
    db_session.flush()

    assert db_session.get(SchemeBenefit, benefit_id) is None
    assert db_session.get(SchemeRequirement, requirement_id) is None
    assert db_session.get(SchemeRequiredDocument, document_id) is None
    assert db_session.get(SchemeApplicationMethod, method_id) is None
    assert db_session.get(SchemeRelatedService, related_id) is None
    # The linked Service itself is untouched — cascade only removes the
    # join row, never the related Service (this phase's §11).
    assert db_session.get(type(linked_service), linked_service.id) is not None


def test_deleting_linked_service_cascades_to_scheme_related_service_row(
    db_session: Session,
) -> None:
    """The reverse direction: removing a `Service` that a scheme links to
    removes the join row too, but must never remove the `Scheme` itself."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)
    linked_service = make_service(db_session, organization=organization, source=source)
    related = make_related_service(db_session, scheme, linked_service)
    related_id, scheme_id = related.id, scheme.id

    db_session.delete(linked_service)
    db_session.flush()

    # The DB-level FK `ondelete="CASCADE"` fires in Postgres itself, but
    # nothing on the `Service` side declares an ORM-level cascade back to
    # `SchemeRelatedService` (only `Scheme.related_services` does) — so
    # the session's identity map doesn't know the row is gone until
    # asked to re-check, same as `test_deleting_department_sets_service_
    # department_to_null`'s identical `expire_all()` need in
    # tests/test_services/test_models.py.
    db_session.expire_all()

    assert db_session.get(SchemeRelatedService, related_id) is None
    assert db_session.get(Scheme, scheme_id) is not None


def test_scheme_related_service_pair_must_be_unique(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)
    linked_service = make_service(db_session, organization=organization, source=source)
    make_related_service(db_session, scheme, linked_service)

    with pytest.raises(IntegrityError):
        make_related_service(db_session, scheme, linked_service)


def test_scheme_soft_delete_field_defaults_to_none(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)

    assert scheme.deleted_at is None
