"""Services domain service-layer tests: list/detail visibility,
filtering, pagination, and Civic Search index synchronization (this
phase's §13). Mirrors tests/test_jobs/test_service.py exactly.
Fixture data is unambiguously fictional (docs/DATA_GOVERNANCE.md §7).
"""

import datetime

from sqlalchemy.orm import Session

from app.search.service import search_documents
from app.services.enums import DeliveryMode, ServiceCategory, ServicePublicationStatus
from app.services.service import (
    SEARCH_ENTITY_TYPE,
    get_service_by_slug,
    is_publicly_visible,
    list_services,
    sync_service_search_index,
)
from app.sources.enums import VerificationStatus
from tests.test_services._helpers import (
    make_application_method,
    make_district,
    make_organization,
    make_required_document,
    make_requirement,
    make_service,
    make_source,
    make_state,
)


def test_published_verified_service_is_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(db_session, organization=organization, source=source)

    assert is_publicly_visible(service) is True


def test_draft_service_is_not_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(
        db_session,
        organization=organization,
        source=source,
        publication_status=ServicePublicationStatus.DRAFT,
    )

    assert is_publicly_visible(service) is False


def test_unverified_service_is_not_publicly_visible_even_if_published(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(
        db_session,
        organization=organization,
        source=source,
        verification_status=VerificationStatus.UNVERIFIED,
    )

    assert is_publicly_visible(service) is False


def test_soft_deleted_service_is_not_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(
        db_session,
        organization=organization,
        source=source,
        deleted_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )

    assert is_publicly_visible(service) is False


def test_get_service_by_slug_returns_none_for_unpublished_service(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_service(
        db_session,
        organization=organization,
        source=source,
        slug="draft-service",
        publication_status=ServicePublicationStatus.DRAFT,
    )

    assert get_service_by_slug(db_session, "draft-service") is None


def test_get_service_by_slug_returns_row_with_joined_names_and_children(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    district = make_district(db_session, state)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(
        db_session,
        organization=organization,
        source=source,
        state=state,
        district=district,
        slug="findable-service",
    )
    make_requirement(db_session, service)
    make_required_document(db_session, service)
    make_application_method(db_session, service)

    row = get_service_by_slug(db_session, "findable-service")

    assert row is not None
    assert row.service.slug == "findable-service"
    assert row.state_name == state.name
    assert row.district_name == district.name
    assert len(row.service.requirements) == 1
    assert len(row.service.required_documents) == 1
    assert len(row.service.application_methods) == 1


def test_get_service_by_slug_returns_none_state_name_when_service_has_no_state(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_service(
        db_session,
        organization=organization,
        source=source,
        state=None,
        district=None,
        slug="statewide-service",
    )

    row = get_service_by_slug(db_session, "statewide-service")

    assert row is not None
    assert row.state_name is None
    assert row.district_name is None


def test_list_services_excludes_unpublished_and_unverified(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_service(db_session, organization=organization, source=source, slug="visible-service")
    make_service(
        db_session,
        organization=organization,
        source=source,
        slug="draft-service",
        publication_status=ServicePublicationStatus.DRAFT,
    )
    make_service(
        db_session,
        organization=organization,
        source=source,
        slug="unverified-service",
        verification_status=VerificationStatus.UNVERIFIED,
    )

    result = list_services(db_session)

    assert result.total_count == 1
    assert result.rows[0].service.slug == "visible-service"


def test_list_services_filters_are_applied_as_and_conditions(db_session: Session) -> None:
    state = make_state(db_session)
    other_state = make_state(db_session, name="Otherland", code="OT", slug="otherland")
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_service(
        db_session,
        organization=organization,
        source=source,
        state=state,
        slug="in-state-service",
        category=ServiceCategory.CERTIFICATES,
    )
    make_service(
        db_session,
        organization=organization,
        source=source,
        state=other_state,
        slug="other-state-service",
        category=ServiceCategory.CERTIFICATES,
    )
    make_service(
        db_session,
        organization=organization,
        source=source,
        state=state,
        slug="welfare-service",
        category=ServiceCategory.WELFARE,
    )

    result = list_services(db_session, state_id=state.id, category=ServiceCategory.CERTIFICATES)

    assert result.total_count == 1
    assert result.rows[0].service.slug == "in-state-service"


def test_list_services_filters_by_delivery_mode(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_service(
        db_session,
        organization=organization,
        source=source,
        slug="online-service",
        delivery_mode=DeliveryMode.ONLINE,
    )
    make_service(
        db_session,
        organization=organization,
        source=source,
        slug="offline-service",
        delivery_mode=DeliveryMode.OFFLINE,
    )

    result = list_services(db_session, delivery_mode=DeliveryMode.ONLINE)

    assert result.total_count == 1
    assert result.rows[0].service.slug == "online-service"


def test_list_services_pagination_is_bounded_and_reports_total_count(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    for index in range(5):
        make_service(db_session, organization=organization, source=source, slug=f"service-{index}")

    result = list_services(db_session, page=1, page_size=2)

    assert result.total_count == 5
    assert len(result.rows) == 2


def test_list_services_orders_by_recency_by_default(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_service(
        db_session,
        organization=organization,
        source=source,
        slug="older-service",
        last_verified_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    make_service(
        db_session,
        organization=organization,
        source=source,
        slug="newer-service",
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )

    result = list_services(db_session)

    assert result.rows[0].service.slug == "newer-service"


def test_sync_service_search_index_indexes_a_publicly_visible_service(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(
        db_session, organization=organization, source=source, name="Findable Certificate Service"
    )

    sync_service_search_index(db_session, service)

    result = search_documents(db_session, q="Findable Certificate Service", locale="en")
    assert result.total_count == 1
    assert result.rows[0].document.entity_type == SEARCH_ENTITY_TYPE
    assert result.rows[0].document.entity_id == service.id


def test_sync_service_search_index_removes_a_service_that_becomes_unpublished(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(
        db_session, organization=organization, source=source, name="Findable Certificate Service"
    )
    sync_service_search_index(db_session, service)
    assert (
        search_documents(db_session, q="Findable Certificate Service", locale="en").total_count == 1
    )

    service.publication_status = ServicePublicationStatus.ARCHIVED
    db_session.flush()
    sync_service_search_index(db_session, service)

    assert (
        search_documents(db_session, q="Findable Certificate Service", locale="en").total_count == 0
    )
