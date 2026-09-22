"""GET /api/v1/schemes, GET /api/v1/schemes/{slug} — exercised against
a real database via the `api_client` fixture (tests/conftest.py), never
mocks, per docs/TESTING.md §3. Mirrors tests/test_services/test_api.py.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.jobs.service import sync_job_search_index
from app.schemes.enums import EducationLevel, SchemeCategory, SchemePublicationStatus
from app.schemes.service import sync_scheme_search_index
from app.services.enums import ServicePublicationStatus
from app.services.service import sync_service_search_index
from tests.test_jobs._helpers import make_job
from tests.test_schemes._helpers import (
    make_application_method,
    make_benefit,
    make_district,
    make_organization,
    make_related_service,
    make_required_document,
    make_requirement,
    make_scheme,
    make_scholarship_detail,
    make_service,
    make_source,
    make_state,
)


def test_list_schemes_returns_only_published_verified_schemes(
    api_client: TestClient, db_session: Session
) -> None:
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

    response = api_client.get("/api/v1/schemes")

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["slug"] == "visible-scheme"
    # No raw database id leaks into the response (docs/API.md §12).
    assert "id" not in body["results"][0]


def test_list_schemes_filters_by_category(api_client: TestClient, db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="pension-scheme",
        category=SchemeCategory.PENSION,
    )
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="scholarship-scheme",
        category=SchemeCategory.SCHOLARSHIP,
    )

    response = api_client.get("/api/v1/schemes", params={"category": "PENSION"})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["slug"] == "pension-scheme"


def test_list_schemes_filters_by_education_level(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    undergrad = make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="undergrad-scholarship",
        category=SchemeCategory.SCHOLARSHIP,
    )
    make_scholarship_detail(db_session, undergrad, education_level=EducationLevel.UNDERGRADUATE)
    postgrad = make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="postgrad-scholarship",
        category=SchemeCategory.SCHOLARSHIP,
    )
    make_scholarship_detail(db_session, postgrad, education_level=EducationLevel.POSTGRADUATE)

    response = api_client.get("/api/v1/schemes", params={"education_level": "UNDERGRADUATE"})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["slug"] == "undergrad-scholarship"


def test_list_schemes_pagination_params_are_honored(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    for index in range(3):
        make_scheme(db_session, organization=organization, source=source, slug=f"scheme-{index}")

    response = api_client.get("/api/v1/schemes", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 3
    assert len(body["results"]) == 2


def test_get_scheme_returns_404_for_unpublished_scheme(
    api_client: TestClient, db_session: Session
) -> None:
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

    response = api_client.get("/api/v1/schemes/draft-scheme")

    assert response.status_code == 404


def test_get_scheme_returns_404_for_nonexistent_slug(
    api_client: TestClient, db_session: Session
) -> None:
    response = api_client.get("/api/v1/schemes/does-not-exist")

    assert response.status_code == 404


def test_get_scheme_returns_full_detail_with_children(
    api_client: TestClient, db_session: Session
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
        slug="detailed-scheme",
    )
    make_benefit(db_session, scheme)
    make_requirement(db_session, scheme)
    make_required_document(db_session, scheme)
    make_application_method(db_session, scheme)
    linked_service = make_service(db_session, organization=organization, source=source)
    make_related_service(
        db_session, scheme, linked_service, note="Apply for this certificate first."
    )
    make_scholarship_detail(
        db_session,
        scheme,
        education_level=EducationLevel.UNDERGRADUATE,
        academic_year="2026-27",
    )

    response = api_client.get("/api/v1/schemes/detailed-scheme")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "detailed-scheme"
    assert len(body["benefits"]) == 1
    assert len(body["requirements"]) == 1
    assert len(body["required_documents"]) == 1
    assert len(body["application_methods"]) == 1
    assert len(body["related_services"]) == 1
    assert body["related_services"][0]["slug"] == linked_service.slug
    assert body["related_services"][0]["note"] == "Apply for this certificate first."
    assert body["scholarship"]["education_level"] == "UNDERGRADUATE"
    assert body["scholarship"]["academic_year"] == "2026-27"
    # No raw database id leaks into the response (docs/API.md §12).
    assert "id" not in body


def test_get_scheme_scholarship_is_null_for_non_scholarship_scheme(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="pension-without-scholarship",
        category=SchemeCategory.PENSION,
    )

    response = api_client.get("/api/v1/schemes/pension-without-scholarship")

    assert response.status_code == 200
    assert response.json()["scholarship"] is None


def test_get_scheme_omits_related_service_that_is_not_publicly_visible(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(
        db_session, organization=organization, source=source, slug="scheme-with-hidden-link"
    )
    hidden_service = make_service(
        db_session,
        organization=organization,
        source=source,
        publication_status=ServicePublicationStatus.DRAFT,
    )
    make_related_service(db_session, scheme, hidden_service)

    response = api_client.get("/api/v1/schemes/scheme-with-hidden-link")

    assert response.status_code == 200
    assert response.json()["related_services"] == []


def test_cross_domain_search_returns_jobs_services_and_schemes(
    api_client: TestClient, db_session: Session
) -> None:
    """The literal Phase 8 acceptance criterion (this phase's §17):
    cross-domain search remains functional once a third domain indexes
    into the same `search_documents` table — Jobs, Services, and
    Schemes must all appear together in one result set."""
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

    scheme = make_scheme(
        db_session,
        organization=organization,
        source=source,
        slug="cross-domain-scheme",
        name="Cross Domain Shared Term Pension",
    )
    sync_scheme_search_index(db_session, scheme)

    response = api_client.get("/api/v1/search", params={"q": "Cross Domain Shared Term"})

    assert response.status_code == 200
    body = response.json()
    entity_types = {result["entity_type"] for result in body["results"]}
    assert entity_types == {"job", "service", "scheme"}
