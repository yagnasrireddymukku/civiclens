"""GET/POST /api/v1/tracking, PATCH/DELETE /api/v1/tracking/{id},
POST .../pause, .../resume — exercised against a real database via the
`api_client` fixture, through the *real* auth flow (register → cookies)
rather than a mocked identity, per docs/TESTING.md §3 and this phase's
explicit "no public endpoint that lets unauthenticated users create or
read arbitrary user tracking data."
"""

import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.jobs.enums import JobNotificationStatus
from app.jobs.service import sync_job_search_index
from app.main import app
from tests.test_documents._helpers import make_organization, make_source, make_state
from tests.test_jobs._helpers import make_job, make_notification


def _register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "a-strong-password-1"}
    )
    assert response.status_code == 201
    return response.json()["csrf_token"]


def test_tracking_requires_authentication(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/tracking")
    assert response.status_code == 401


def test_track_requires_csrf_token(api_client: TestClient, db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    _register(api_client, "csrf-required@example-test.invalid")

    response = api_client.post(
        "/api/v1/tracking", json={"entity_type": "job", "entity_slug": job.slug}
    )
    assert response.status_code == 403


def test_track_an_entity_and_list_it(api_client: TestClient, db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        title="Test Civic Clerk Recruitment (Fixture)",
    )
    sync_job_search_index(db_session, job)
    csrf_token = _register(api_client, "tracker@example-test.invalid")

    track_response = api_client.post(
        "/api/v1/tracking",
        json={"entity_type": "job", "entity_slug": job.slug, "label": "My dream job"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert track_response.status_code == 201
    body = track_response.json()
    assert body["entity_type"] == "job"
    assert body["title"] == "Test Civic Clerk Recruitment (Fixture)"
    assert body["label"] == "My dream job"
    assert body["still_available"] is True

    list_response = api_client.get("/api/v1/tracking")
    assert list_response.status_code == 200
    assert len(list_response.json()["results"]) == 1


def test_track_an_unknown_entity_404s(api_client: TestClient) -> None:
    csrf_token = _register(api_client, "tracker2@example-test.invalid")
    response = api_client.post(
        "/api/v1/tracking",
        json={"entity_type": "job", "entity_slug": "does-not-exist"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 404


def test_pause_resume_and_remove_a_tracked_item(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    csrf_token = _register(api_client, "pauser@example-test.invalid")
    headers = {"X-CSRF-Token": csrf_token}

    track_response = api_client.post(
        "/api/v1/tracking", json={"entity_type": "job", "entity_slug": job.slug}, headers=headers
    )
    item_id = track_response.json()["id"]

    pause_response = api_client.post(f"/api/v1/tracking/{item_id}/pause", headers=headers)
    assert pause_response.status_code == 200
    assert pause_response.json()["is_active"] is False

    resume_response = api_client.post(f"/api/v1/tracking/{item_id}/resume", headers=headers)
    assert resume_response.status_code == 200
    assert resume_response.json()["is_active"] is True

    delete_response = api_client.delete(f"/api/v1/tracking/{item_id}", headers=headers)
    assert delete_response.status_code == 204

    list_response = api_client.get("/api/v1/tracking")
    assert list_response.json()["results"] == []


def test_cannot_pause_or_remove_another_users_tracked_item(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)

    owner_csrf = _register(api_client, "owner@example-test.invalid")
    track_response = api_client.post(
        "/api/v1/tracking",
        json={"entity_type": "job", "entity_slug": job.slug},
        headers={"X-CSRF-Token": owner_csrf},
    )
    item_id = track_response.json()["id"]

    # A second, independent authenticated identity against the same
    # shared test database.
    attacker_client = TestClient(app)
    attacker_csrf = _register(attacker_client, "attacker@example-test.invalid")

    pause_response = attacker_client.post(
        f"/api/v1/tracking/{item_id}/pause", headers={"X-CSRF-Token": attacker_csrf}
    )
    assert pause_response.status_code == 404

    delete_response = attacker_client.delete(
        f"/api/v1/tracking/{item_id}", headers={"X-CSRF-Token": attacker_csrf}
    )
    assert delete_response.status_code == 404

    # And the owner's own view of it is unaffected.
    owner_list = api_client.get("/api/v1/tracking")
    assert len(owner_list.json()["results"]) == 1


def test_list_tracking_includes_deadline_information(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    make_notification(
        db_session,
        job,
        source=source,
        status=JobNotificationStatus.PUBLISHED,
        application_end=datetime.date(2026, 12, 31),
    )
    csrf_token = _register(api_client, "deadline-viewer@example-test.invalid")

    api_client.post(
        "/api/v1/tracking",
        json={"entity_type": "job", "entity_slug": job.slug},
        headers={"X-CSRF-Token": csrf_token},
    )
    response = api_client.get("/api/v1/tracking")
    result = response.json()["results"][0]
    assert result["deadline"] == "2026-12-31"
    assert result["deadline_expired"] is False
