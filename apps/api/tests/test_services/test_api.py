"""GET /api/v1/services, GET /api/v1/services/{slug} — exercised against
a real database via the `api_client` fixture (tests/conftest.py), never
mocks, per docs/TESTING.md §3. Mirrors tests/test_jobs/test_api.py.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.jobs.service import sync_job_search_index
from app.services.enums import DeliveryMode, ServicePublicationStatus
from app.services.service import sync_service_search_index
from tests.test_jobs._helpers import make_job
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


def test_list_services_returns_only_published_verified_services(
    api_client: TestClient, db_session: Session
) -> None:
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

    response = api_client.get("/api/v1/services")

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["slug"] == "visible-service"
    # No raw database id leaks into the response (docs/API.md §12).
    assert "id" not in body["results"][0]


def test_list_services_filters_by_category_and_delivery_mode(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_service(
        db_session,
        organization=organization,
        source=source,
        slug="online-certificate",
        delivery_mode=DeliveryMode.ONLINE,
    )
    make_service(
        db_session,
        organization=organization,
        source=source,
        slug="offline-certificate",
        delivery_mode=DeliveryMode.OFFLINE,
    )

    response = api_client.get("/api/v1/services", params={"delivery_mode": "ONLINE"})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["slug"] == "online-certificate"


def test_list_services_pagination_params_are_honored(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    for index in range(3):
        make_service(db_session, organization=organization, source=source, slug=f"service-{index}")

    response = api_client.get("/api/v1/services", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 3
    assert len(body["results"]) == 2


def test_list_services_rejects_unknown_query_parameters(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/services", params={"sort_by_popularity": "true"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_service_detail_includes_requirements_documents_and_methods(
    api_client: TestClient, db_session: Session
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
        slug="detailed-service",
    )
    make_requirement(db_session, service, description="Must be 18 or older (fictional fixture).")
    make_required_document(db_session, service, name="Aadhaar Card (Fixture)")
    make_application_method(
        db_session, service, url="https://example-test.invalid/apply/detailed-service"
    )

    response = api_client.get("/api/v1/services/detailed-service")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "detailed-service"
    assert body["state"] == state.name
    assert body["district"] == district.name
    assert body["requirements"][0]["description"] == "Must be 18 or older (fictional fixture)."
    assert body["required_documents"][0]["name"] == "Aadhaar Card (Fixture)"
    assert (
        body["application_methods"][0]["url"]
        == "https://example-test.invalid/apply/detailed-service"
    )
    assert body["source"]["organization"] == source.organization


def test_get_service_detail_404s_for_an_unpublished_service(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_service(
        db_session,
        organization=organization,
        source=source,
        slug="hidden-service",
        publication_status=ServicePublicationStatus.DRAFT,
    )

    response = api_client.get("/api/v1/services/hidden-service")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_get_service_detail_404s_for_a_nonexistent_slug(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/services/does-not-exist")

    assert response.status_code == 404


def test_indexed_service_is_findable_via_the_generic_search_endpoint(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    service = make_service(
        db_session,
        organization=organization,
        source=source,
        slug="cross-endpoint-service",
        name="Cross Endpoint Test Certificate",
    )
    sync_service_search_index(db_session, service)

    response = api_client.get(
        "/api/v1/search", params={"q": "Cross Endpoint Test Certificate", "locale": "en"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["route"] == "/services/cross-endpoint-service"
    assert body["results"][0]["entity_type"] == "service"


def test_cross_domain_search_returns_both_jobs_and_services(
    api_client: TestClient, db_session: Session
) -> None:
    """The literal Phase 7 acceptance criterion: cross-domain search
    remains functional once a second domain indexes into the same
    `search_documents` table."""
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)

    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="cross-domain-job",
        title="Cross Domain Shared Term Clerk",
    )
    sync_job_search_index(db_session, job)

    service = make_service(
        db_session,
        organization=organization,
        source=source,
        slug="cross-domain-service",
        name="Cross Domain Shared Term Certificate",
    )
    sync_service_search_index(db_session, service)

    response = api_client.get("/api/v1/search", params={"q": "Cross Domain Shared Term"})

    assert response.status_code == 200
    body = response.json()
    entity_types = {result["entity_type"] for result in body["results"]}
    assert entity_types == {"job", "service"}
