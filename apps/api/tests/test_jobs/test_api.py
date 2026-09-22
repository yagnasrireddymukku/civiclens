"""GET /api/v1/jobs, GET /api/v1/jobs/{slug} — exercised against a real
database via the `api_client` fixture (tests/conftest.py), never mocks,
per docs/TESTING.md §3.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.jobs.enums import JobPublicationStatus
from app.jobs.service import sync_job_search_index
from tests.test_jobs._helpers import (
    make_department,
    make_district,
    make_job,
    make_notification,
    make_organization,
    make_source,
    make_state,
    make_vacancy,
)


def test_list_jobs_returns_only_published_verified_jobs(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(db_session, organization=organization, state=state, source=source, slug="visible-job")
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="draft-job",
        publication_status=JobPublicationStatus.DRAFT,
    )

    response = api_client.get("/api/v1/jobs")

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["slug"] == "visible-job"
    # No raw database id leaks into the response (docs/API.md §12).
    assert "id" not in body["results"][0]


def test_list_jobs_filters_by_state_and_employment_type(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    other_state = make_state(db_session, name="Otherland", code="OT", slug="otherland")
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(db_session, organization=organization, state=state, source=source, slug="in-state")
    make_job(
        db_session, organization=organization, state=other_state, source=source, slug="other-state"
    )

    response = api_client.get("/api/v1/jobs", params={"state_id": str(state.id)})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["slug"] == "in-state"


def test_list_jobs_pagination_params_are_honored(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    for index in range(3):
        make_job(
            db_session, organization=organization, state=state, source=source, slug=f"job-{index}"
        )

    response = api_client.get("/api/v1/jobs", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 3
    assert len(body["results"]) == 2


def test_list_jobs_rejects_unknown_query_parameters(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/jobs", params={"sort_by_popularity": "true"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_job_detail_includes_notifications_and_vacancies(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    district = make_district(db_session, state)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    department = make_department(db_session, state, organization=organization)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        department=department,
        district=district,
        slug="detailed-job",
    )
    notification = make_notification(db_session, job, source)
    make_vacancy(db_session, notification, post_name="Junior Clerk")

    response = api_client.get("/api/v1/jobs/detailed-job")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "detailed-job"
    assert body["state"] == state.name
    assert body["district"] == district.name
    assert body["department"]["name"] == department.name
    assert len(body["notifications"]) == 1
    assert body["notifications"][0]["vacancies"][0]["post_name"] == "Junior Clerk"
    assert body["source"]["organization"] == source.organization


def test_get_job_detail_404s_for_an_unpublished_job(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="hidden-job",
        publication_status=JobPublicationStatus.DRAFT,
    )

    response = api_client.get("/api/v1/jobs/hidden-job")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_get_job_detail_404s_for_a_nonexistent_slug(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/jobs/does-not-exist")

    assert response.status_code == 404


def test_indexed_job_is_findable_via_the_generic_search_endpoint(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        slug="cross-endpoint-job",
        title="Cross Endpoint Test Clerk",
    )
    sync_job_search_index(db_session, job)

    response = api_client.get(
        "/api/v1/search", params={"q": "Cross Endpoint Test Clerk", "locale": "en"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert body["results"][0]["route"] == "/jobs/cross-endpoint-job"
