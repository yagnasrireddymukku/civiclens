"""Schemes domain service-layer tests: list/detail visibility,
filtering, pagination, and Civic Search index synchronization (this
phase's §16). Mirrors tests/test_services/test_service.py exactly.
Fixture data is unambiguously fictional (docs/DATA_GOVERNANCE.md §7).
"""

import datetime

from sqlalchemy.orm import Session

from app.schemes.enums import SchemeCategory, SchemePublicationStatus
from app.schemes.service import (
    SEARCH_ENTITY_TYPE,
    get_scheme_by_slug,
    is_publicly_visible,
    list_schemes,
    sync_scheme_search_index,
)
from app.search.service import search_documents
from app.sources.enums import VerificationStatus
from tests.test_schemes._helpers import (
    make_application_method,
    make_benefit,
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


def test_published_verified_scheme_is_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)

    assert is_publicly_visible(scheme) is True


def test_draft_scheme_is_not_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(
        db_session,
        organization=organization,
        source=source,
        publication_status=SchemePublicationStatus.DRAFT,
    )

    assert is_publicly_visible(scheme) is False


def test_unverified_scheme_is_not_publicly_visible_even_if_published(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(
        db_session,
        organization=organization,
        source=source,
        verification_status=VerificationStatus.UNVERIFIED,
    )

    assert is_publicly_visible(scheme) is False


def test_soft_deleted_scheme_is_not_publicly_visible(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(
        db_session,
        organization=organization,
        source=source,
        deleted_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )

    assert is_publicly_visible(scheme) is False


def test_get_scheme_by_slug_returns_none_for_unpublished_scheme(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="draft-scheme",
        publication_status=SchemePublicationStatus.DRAFT,
    )

    assert get_scheme_by_slug(db_session, "draft-scheme") is None


def test_get_scheme_by_slug_returns_row_with_joined_names_and_children(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    district = make_district(db_session, state)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(
        db_session,
        organization=organization,
        source=source,
        state=state,
        district=district,
        slug="findable-scheme",
    )
    make_benefit(db_session, scheme)
    make_requirement(db_session, scheme)
    make_required_document(db_session, scheme)
    make_application_method(db_session, scheme)
    linked_service = make_service(db_session, organization=organization, source=source)
    make_related_service(db_session, scheme, linked_service)

    row = get_scheme_by_slug(db_session, "findable-scheme")

    assert row is not None
    assert row.scheme.slug == "findable-scheme"
    assert row.state_name == state.name
    assert row.district_name == district.name
    assert len(row.scheme.benefits) == 1
    assert len(row.scheme.requirements) == 1
    assert len(row.scheme.required_documents) == 1
    assert len(row.scheme.application_methods) == 1
    assert len(row.scheme.related_services) == 1
    assert row.scheme.related_services[0].service_id == linked_service.id


def test_get_scheme_by_slug_returns_none_state_name_when_scheme_has_no_state(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        state=None,
        district=None,
        slug="statewide-scheme",
    )

    row = get_scheme_by_slug(db_session, "statewide-scheme")

    assert row is not None
    assert row.state_name is None
    assert row.district_name is None


def test_list_schemes_excludes_unpublished_and_unverified(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_scheme(db_session, organization=organization, source=source, slug="visible-scheme")
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="draft-scheme",
        publication_status=SchemePublicationStatus.DRAFT,
    )
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="unverified-scheme",
        verification_status=VerificationStatus.UNVERIFIED,
    )

    result = list_schemes(db_session)

    assert result.total_count == 1
    assert result.rows[0].scheme.slug == "visible-scheme"


def test_list_schemes_filters_are_applied_as_and_conditions(db_session: Session) -> None:
    state = make_state(db_session)
    other_state = make_state(db_session, name="Otherland", code="OT", slug="otherland")
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        state=state,
        slug="in-state-scheme",
        category=SchemeCategory.PENSION,
    )
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        state=other_state,
        slug="other-state-scheme",
        category=SchemeCategory.PENSION,
    )
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        state=state,
        slug="scholarship-scheme",
        category=SchemeCategory.SCHOLARSHIP,
    )

    result = list_schemes(db_session, state_id=state.id, category=SchemeCategory.PENSION)

    assert result.total_count == 1
    assert result.rows[0].scheme.slug == "in-state-scheme"


def test_list_schemes_pagination_is_bounded_and_reports_total_count(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    for index in range(5):
        make_scheme(db_session, organization=organization, source=source, slug=f"scheme-{index}")

    result = list_schemes(db_session, page=1, page_size=2)

    assert result.total_count == 5
    assert len(result.rows) == 2


def test_list_schemes_orders_by_recency_by_default(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="older-scheme",
        last_verified_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="newer-scheme",
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )

    result = list_schemes(db_session)

    assert result.rows[0].scheme.slug == "newer-scheme"


def test_sync_scheme_search_index_indexes_a_publicly_visible_scheme(db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(
        db_session, organization=organization, source=source, name="Findable Pension Scheme"
    )

    sync_scheme_search_index(db_session, scheme)

    result = search_documents(db_session, q="Findable Pension Scheme", locale="en")
    assert result.total_count == 1
    assert result.rows[0].document.entity_type == SEARCH_ENTITY_TYPE
    assert result.rows[0].document.entity_id == scheme.id


def test_sync_scheme_search_index_removes_a_scheme_that_becomes_unpublished(
    db_session: Session,
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(
        db_session, organization=organization, source=source, name="Findable Pension Scheme"
    )
    sync_scheme_search_index(db_session, scheme)
    assert search_documents(db_session, q="Findable Pension Scheme", locale="en").total_count == 1

    scheme.publication_status = SchemePublicationStatus.ARCHIVED
    db_session.flush()
    sync_scheme_search_index(db_session, scheme)

    assert search_documents(db_session, q="Findable Pension Scheme", locale="en").total_count == 0
