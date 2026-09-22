"""GET /api/v1/documents, GET /api/v1/documents/{slug} — exercised
against a real database via the `api_client` fixture
(tests/conftest.py), never mocks, per docs/TESTING.md §3. Mirrors
tests/test_schemes/test_api.py.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.documents.enums import DocumentCategory, DocumentPublicationStatus, DocumentType
from app.documents.service import sync_document_search_index
from app.jobs.service import sync_job_search_index
from app.schemes.service import sync_scheme_search_index
from app.services.enums import ServicePublicationStatus
from app.services.service import sync_service_search_index
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
from tests.test_jobs._helpers import make_job


def test_list_documents_returns_only_published_verified_documents(
    api_client: TestClient, db_session: Session
) -> None:
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

    response = api_client.get("/api/v1/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["slug"] == "visible-document"
    # No raw database id leaks into the response (docs/API.md §12).
    assert "id" not in body["results"][0]


def test_list_documents_filters_by_document_type_and_category(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_document(
        db_session,
        organization=organization,
        source=source,
        slug="income-certificate",
        document_type=DocumentType.CERTIFICATE,
        category=DocumentCategory.INCOME,
    )
    make_document(
        db_session,
        organization=organization,
        source=source,
        slug="identity-card",
        document_type=DocumentType.IDENTITY_DOCUMENT,
        category=DocumentCategory.IDENTITY,
    )

    response = api_client.get(
        "/api/v1/documents", params={"document_type": "CERTIFICATE", "category": "INCOME"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["slug"] == "income-certificate"


def test_list_documents_pagination_params_are_honored(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    for index in range(3):
        make_document(
            db_session, organization=organization, source=source, slug=f"document-{index}"
        )

    response = api_client.get("/api/v1/documents", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 3
    assert len(body["results"]) == 2


def test_get_document_returns_404_for_unpublished_document(
    api_client: TestClient, db_session: Session
) -> None:
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

    response = api_client.get("/api/v1/documents/draft-document")

    assert response.status_code == 404


def test_get_document_returns_404_for_nonexistent_slug(
    api_client: TestClient, db_session: Session
) -> None:
    response = api_client.get("/api/v1/documents/does-not-exist")

    assert response.status_code == 404


def test_get_document_returns_full_detail_with_children(
    api_client: TestClient, db_session: Session
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
        slug="detailed-document",
        service_id=linked_service.id,
    )
    make_requirement(db_session, document)
    referenced = make_document(
        db_session, organization=organization, source=source, slug="referenced-document"
    )
    make_supporting_document(db_session, document, civic_document_id=referenced.id)
    make_application_method(db_session, document)
    scheme = make_scheme(db_session, organization=organization, source=source)
    make_scheme_required_document(db_session, scheme, civic_document_id=document.id)

    response = api_client.get("/api/v1/documents/detailed-document")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "detailed-document"
    assert len(body["requirements"]) == 1
    assert len(body["supporting_documents"]) == 1
    assert body["supporting_documents"][0]["civic_document"]["slug"] == "referenced-document"
    assert len(body["application_methods"]) == 1
    assert body["service"]["slug"] == linked_service.slug
    assert len(body["required_by"]) == 1
    assert body["required_by"][0] == {
        "entity_type": "scheme",
        "slug": scheme.slug,
        "name": scheme.name,
    }
    # No raw database id leaks into the response (docs/API.md §12).
    assert "id" not in body


def test_get_document_omits_service_that_is_not_publicly_visible(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    hidden_service = make_service(
        db_session,
        organization=organization,
        source=source,
        publication_status=ServicePublicationStatus.DRAFT,
    )
    document = make_document(
        db_session,
        organization=organization,
        source=source,
        slug="document-with-hidden-service",
        service_id=hidden_service.id,
    )

    response = api_client.get(f"/api/v1/documents/{document.slug}")

    assert response.status_code == 200
    assert response.json()["service"] is None


def test_get_document_required_by_never_infers_from_matching_names(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    document = make_document(db_session, organization=organization, source=source)
    service = make_service(db_session, organization=organization, source=source)
    make_service_required_document(db_session, service, name=document.name)

    response = api_client.get(f"/api/v1/documents/{document.slug}")

    assert response.status_code == 200
    assert response.json()["required_by"] == []


def test_cross_domain_search_returns_jobs_services_schemes_and_documents(
    api_client: TestClient, db_session: Session
) -> None:
    """The literal Phase 10 acceptance criterion (this phase's §18):
    cross-domain search remains functional once a fourth domain indexes
    into the same `search_documents` table — Jobs, Services, Schemes,
    and Documents must all appear together in one result set."""
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
        name="Cross Domain Shared Term Certificate Issuance",
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

    document = make_document(
        db_session,
        organization=organization,
        source=source,
        slug="cross-domain-document",
        name="Cross Domain Shared Term Income Certificate",
    )
    sync_document_search_index(db_session, document)

    response = api_client.get("/api/v1/search", params={"q": "Cross Domain Shared Term"})

    assert response.status_code == 200
    body = response.json()
    entity_types = {result["entity_type"] for result in body["results"]}
    assert entity_types == {"job", "service", "scheme", "document"}
