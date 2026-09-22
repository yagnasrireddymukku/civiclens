"""Documents domain service-layer tests: list/detail visibility,
filtering, pagination, Civic Search index synchronization, and the
"required by" reverse relationship (this phase's §14/§22). Mirrors
tests/test_schemes/test_service.py exactly. Fixture data is
unambiguously fictional (docs/DATA_GOVERNANCE.md §7).
"""

import datetime

from sqlalchemy.orm import Session

from app.documents.enums import DocumentCategory, DocumentPublicationStatus, DocumentType
from app.documents.service import (
    SEARCH_ENTITY_TYPE,
    get_document_by_slug,
    get_required_by,
    is_publicly_visible,
    list_documents,
    sync_document_search_index,
)
from app.requirements.enums import DeliveryMode
from app.schemes.enums import SchemePublicationStatus
from app.search.service import search_documents
from app.services.enums import ServicePublicationStatus
from app.sources.enums import VerificationStatus
from tests.test_documents._helpers import (
    make_application_method,
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


def test_published_verified_document_is_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)

    assert is_publicly_visible(document) is True


def test_draft_document_is_not_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(
        db_session,
        organization=organization,
        source=source,
        publication_status=DocumentPublicationStatus.DRAFT,
    )

    assert is_publicly_visible(document) is False


def test_unverified_document_is_not_publicly_visible_even_if_published(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(
        db_session,
        organization=organization,
        source=source,
        verification_status=VerificationStatus.UNVERIFIED,
    )

    assert is_publicly_visible(document) is False


def test_soft_deleted_document_is_not_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(
        db_session,
        organization=organization,
        source=source,
        deleted_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )

    assert is_publicly_visible(document) is False


def test_get_document_by_slug_returns_none_for_unpublished_document(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_document(
        db_session,
        organization=organization,
        source=source,
        slug="draft-document",
        publication_status=DocumentPublicationStatus.DRAFT,
    )

    assert get_document_by_slug(db_session, "draft-document") is None


def test_get_document_by_slug_returns_row_with_joined_names_and_children(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    district = make_district(db_session, state)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    linked_service = make_service(db_session, organization=organization, source=source)
    document = make_document(
        db_session,
        organization=organization,
        source=source,
        state=state,
        district=district,
        slug="findable-document",
        service_id=linked_service.id,
    )
    make_requirement(db_session, document)
    referenced = make_document(db_session, organization=organization, source=source)
    make_supporting_document(db_session, document, civic_document_id=referenced.id)
    make_application_method(db_session, document)

    row = get_document_by_slug(db_session, "findable-document")

    assert row is not None
    assert row.document.slug == "findable-document"
    assert row.state_name == state.name
    assert row.district_name == district.name
    assert len(row.document.requirements) == 1
    assert len(row.document.supporting_documents) == 1
    assert row.document.supporting_documents[0].civic_document is referenced
    assert len(row.document.application_methods) == 1
    assert row.document.service is linked_service


def test_get_document_by_slug_returns_none_state_name_when_document_has_no_state(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_document(
        db_session,
        organization=organization,
        source=source,
        state=None,
        district=None,
        slug="statewide-document",
    )

    row = get_document_by_slug(db_session, "statewide-document")

    assert row is not None
    assert row.state_name is None
    assert row.district_name is None


def test_list_documents_excludes_unpublished_and_unverified(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_document(db_session, organization=organization, source=source, slug="visible-document")
    make_document(
        db_session,
        organization=organization,
        source=source,
        slug="draft-document",
        publication_status=DocumentPublicationStatus.DRAFT,
    )
    make_document(
        db_session,
        organization=organization,
        source=source,
        slug="unverified-document",
        verification_status=VerificationStatus.UNVERIFIED,
    )

    result = list_documents(db_session)

    assert result.total_count == 1
    assert result.rows[0].document.slug == "visible-document"


def test_list_documents_filters_are_applied_as_and_conditions(db_session: Session) -> None:
    state = make_state(db_session)
    other_state = make_state(db_session, name="Otherland", code="OT", slug="otherland")
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_document(
        db_session,
        organization=organization,
        source=source,
        state=state,
        slug="in-state-document",
        category=DocumentCategory.INCOME,
    )
    make_document(
        db_session,
        organization=organization,
        source=source,
        state=other_state,
        slug="other-state-document",
        category=DocumentCategory.INCOME,
    )
    make_document(
        db_session,
        organization=organization,
        source=source,
        state=state,
        slug="residence-document",
        category=DocumentCategory.RESIDENCE,
    )

    result = list_documents(db_session, state_id=state.id, category=DocumentCategory.INCOME)

    assert result.total_count == 1
    assert result.rows[0].document.slug == "in-state-document"


def test_list_documents_filters_by_document_type_and_delivery_mode(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_document(
        db_session,
        organization=organization,
        source=source,
        slug="online-certificate",
        document_type=DocumentType.CERTIFICATE,
        delivery_mode=DeliveryMode.ONLINE,
    )
    make_document(
        db_session,
        organization=organization,
        source=source,
        slug="offline-permit",
        document_type=DocumentType.PERMIT,
        delivery_mode=DeliveryMode.OFFLINE,
    )

    result = list_documents(
        db_session, document_type=DocumentType.CERTIFICATE, delivery_mode=DeliveryMode.ONLINE
    )

    assert result.total_count == 1
    assert result.rows[0].document.slug == "online-certificate"


def test_list_documents_pagination_is_bounded_and_reports_total_count(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    for index in range(5):
        make_document(
            db_session, organization=organization, source=source, slug=f"document-{index}"
        )

    result = list_documents(db_session, page=1, page_size=2)

    assert result.total_count == 5
    assert len(result.rows) == 2


def test_list_documents_orders_by_recency_by_default(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_document(
        db_session,
        organization=organization,
        source=source,
        slug="older-document",
        last_verified_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    make_document(
        db_session,
        organization=organization,
        source=source,
        slug="newer-document",
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )

    result = list_documents(db_session)

    assert result.rows[0].document.slug == "newer-document"


def test_sync_document_search_index_indexes_a_publicly_visible_document(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(
        db_session, organization=organization, source=source, name="Findable Income Certificate"
    )

    sync_document_search_index(db_session, document)

    result = search_documents(db_session, q="Findable Income Certificate", locale="en")
    assert result.total_count == 1
    assert result.rows[0].document.entity_type == SEARCH_ENTITY_TYPE
    assert result.rows[0].document.entity_id == document.id


def test_sync_document_search_index_removes_a_document_that_becomes_unpublished(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(
        db_session, organization=organization, source=source, name="Findable Income Certificate"
    )
    sync_document_search_index(db_session, document)
    assert (
        search_documents(db_session, q="Findable Income Certificate", locale="en").total_count == 1
    )

    document.publication_status = DocumentPublicationStatus.ARCHIVED
    db_session.flush()
    sync_document_search_index(db_session, document)

    assert (
        search_documents(db_session, q="Findable Income Certificate", locale="en").total_count == 0
    )


def test_get_required_by_returns_services_and_schemes_that_reference_the_document(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)
    service = make_service(
        db_session, organization=organization, source=source, name="Test Service"
    )
    scheme = make_scheme(db_session, organization=organization, source=source, name="Test Scheme")
    make_service_required_document(db_session, service, civic_document_id=document.id)
    make_scheme_required_document(db_session, scheme, civic_document_id=document.id)

    required_by = get_required_by(db_session, document.id)

    entries = {(entry.entity_type, entry.slug) for entry in required_by}
    assert entries == {("service", service.slug), ("scheme", scheme.slug)}


def test_get_required_by_excludes_records_that_are_not_publicly_visible(
    db_session: Session,
) -> None:
    """Only show relationships that are explicitly modeled — but never
    leak a hidden record's existence through the reverse lookup either
    (this phase's §16/§22)."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)
    hidden_service = make_service(
        db_session,
        organization=organization,
        source=source,
        publication_status=ServicePublicationStatus.DRAFT,
    )
    hidden_scheme = make_scheme(
        db_session,
        organization=organization,
        source=source,
        publication_status=SchemePublicationStatus.DRAFT,
    )
    make_service_required_document(db_session, hidden_service, civic_document_id=document.id)
    make_scheme_required_document(db_session, hidden_scheme, civic_document_id=document.id)

    assert get_required_by(db_session, document.id) == []


def test_get_required_by_never_infers_from_matching_names(db_session: Session) -> None:
    """This phase's §22 explicit prohibition: a `RequiredDocument`/
    `SchemeRequiredDocument` row with the *same name* as a document but
    no `civic_document_id` link must never appear in `required_by`."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)
    service = make_service(db_session, organization=organization, source=source)
    make_service_required_document(db_session, service, name=document.name, civic_document_id=None)

    assert get_required_by(db_session, document.id) == []
