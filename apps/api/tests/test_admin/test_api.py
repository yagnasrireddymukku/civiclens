"""HTTP-level tests for /api/v1/admin/* — real role enforcement (401
for signed-out, 403 for a signed-in `user`, 200 for `editor`/`admin`),
CSRF enforcement on mutating routes, rate limiting, and full request/
response round trips. Users are given a real session via the actual
`/auth/login` flow (never a header/query-param role override — "never
trust role information supplied by the client").
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.main import app
from app.sources.enums import ChangeReviewStatus, VerificationStatus
from app.tracking.enums import TrackedEntityType
from app.users.enums import UserRole
from tests.test_auth._helpers import make_user
from tests.test_documents._helpers import make_organization, make_state
from tests.test_jobs._helpers import make_job
from tests.test_tracking._helpers import make_change_record, make_source

_PASSWORD = "Correct-Horse-Battery-Staple"


def _login(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": _PASSWORD})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _job_fixture(db_session: Session):
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    return job, source


def test_admin_dashboard_requires_authentication(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/admin/dashboard")
    assert response.status_code == 401


def test_admin_dashboard_rejects_an_ordinary_user(
    api_client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="plain-user@example-test.invalid", role=UserRole.USER)
    _login(api_client, user.email)

    response = api_client.get("/api/v1/admin/dashboard")
    assert response.status_code == 403


def test_admin_dashboard_allows_an_editor(api_client: TestClient, db_session: Session) -> None:
    editor = make_user(db_session, email="editor@example-test.invalid", role=UserRole.EDITOR)
    _login(api_client, editor.email)

    response = api_client.get("/api/v1/admin/dashboard")
    assert response.status_code == 200
    assert "pending_change_records" in response.json()


def test_admin_dashboard_allows_an_admin(api_client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, email="admin@example-test.invalid", role=UserRole.ADMIN)
    _login(api_client, admin.email)

    response = api_client.get("/api/v1/admin/dashboard")
    assert response.status_code == 200


def test_list_change_records_requires_reviewer_role(
    api_client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="plain-user-2@example-test.invalid", role=UserRole.USER)
    _login(api_client, user.email)

    response = api_client.get("/api/v1/admin/change-records")
    assert response.status_code == 403


def test_approve_change_record_requires_csrf_token(
    api_client: TestClient, db_session: Session
) -> None:
    job, _source = _job_fixture(db_session)
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
    )
    editor = make_user(db_session, email="editor-csrf@example-test.invalid", role=UserRole.EDITOR)
    _login(api_client, editor.email)

    response = api_client.post(f"/api/v1/admin/change-records/{record.id}/approve")
    assert response.status_code == 403


def test_approve_change_record_end_to_end(api_client: TestClient, db_session: Session) -> None:
    job, _source = _job_fixture(db_session)
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
    )
    editor = make_user(
        db_session, email="editor-approve@example-test.invalid", role=UserRole.EDITOR
    )
    csrf = _login(api_client, editor.email)

    response = api_client.post(
        f"/api/v1/admin/change-records/{record.id}/approve", headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "APPROVED"
    assert body["applied_at"] is not None


def test_reject_an_already_approved_record_returns_409(
    api_client: TestClient, db_session: Session
) -> None:
    job, _source = _job_fixture(db_session)
    record = make_change_record(
        db_session,
        entity_type=TrackedEntityType.JOB,
        entity_id=job.id,
        field="publication_status",
        old_value="DRAFT",
        new_value="PUBLISHED",
        review_status=ChangeReviewStatus.APPROVED,
    )
    editor = make_user(
        db_session, email="editor-conflict@example-test.invalid", role=UserRole.EDITOR
    )
    csrf = _login(api_client, editor.email)

    response = api_client.post(
        f"/api/v1/admin/change-records/{record.id}/reject", headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 409


def test_approve_nonexistent_change_record_returns_404(
    api_client: TestClient, db_session: Session
) -> None:
    editor = make_user(db_session, email="editor-404@example-test.invalid", role=UserRole.EDITOR)
    csrf = _login(api_client, editor.email)

    response = api_client.post(
        "/api/v1/admin/change-records/00000000-0000-0000-0000-000000000000/approve",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 404


def test_submit_verification_end_to_end(api_client: TestClient, db_session: Session) -> None:
    job, source = _job_fixture(db_session)
    editor = make_user(db_session, email="editor-verify@example-test.invalid", role=UserRole.EDITOR)
    csrf = _login(api_client, editor.email)

    response = api_client.post(
        f"/api/v1/admin/verification/job/{job.id}",
        json={"status": "VERIFIED", "source_id": str(source.id)},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "VERIFIED"
    assert body["source_id"] == str(source.id)


def test_submit_verification_without_a_source_id_is_rejected(
    api_client: TestClient, db_session: Session
) -> None:
    job, _source = _job_fixture(db_session)
    editor = make_user(
        db_session, email="editor-no-evidence@example-test.invalid", role=UserRole.EDITOR
    )
    csrf = _login(api_client, editor.email)

    response = api_client.post(
        f"/api/v1/admin/verification/job/{job.id}",
        json={"status": "VERIFIED"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422


def test_get_verification_queue_end_to_end(api_client: TestClient, db_session: Session) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        verification_status=VerificationStatus.NEEDS_REVIEW,
    )
    editor = make_user(db_session, email="editor-queue@example-test.invalid", role=UserRole.EDITOR)
    _login(api_client, editor.email)

    response = api_client.get("/api/v1/admin/verification/queue")
    assert response.status_code == 200
    assert response.json()["pagination"]["total_count"] == 1


def test_list_and_get_sources_end_to_end(api_client: TestClient, db_session: Session) -> None:
    source = make_source(db_session)
    editor = make_user(
        db_session, email="editor-sources@example-test.invalid", role=UserRole.EDITOR
    )
    _login(api_client, editor.email)

    list_response = api_client.get("/api/v1/admin/sources")
    assert list_response.status_code == 200
    assert list_response.json()["pagination"]["total_count"] == 1

    detail_response = api_client.get(f"/api/v1/admin/sources/{source.id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["versions"] == []


def test_get_nonexistent_source_returns_404(api_client: TestClient, db_session: Session) -> None:
    editor = make_user(
        db_session, email="editor-source-404@example-test.invalid", role=UserRole.EDITOR
    )
    _login(api_client, editor.email)

    response = api_client.get("/api/v1/admin/sources/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_admin_rate_limit_returns_429_after_the_configured_number_of_requests(
    api_client: TestClient, db_session: Session, monkeypatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_rate_limit_requests", 2)
    editor = make_user(
        db_session, email="editor-ratelimit@example-test.invalid", role=UserRole.EDITOR
    )
    csrf = _login(api_client, editor.email)

    first = api_client.post(
        "/api/v1/admin/change-records/00000000-0000-0000-0000-000000000000/approve",
        headers={"X-CSRF-Token": csrf},
    )
    second = api_client.post(
        "/api/v1/admin/change-records/00000000-0000-0000-0000-000000000000/approve",
        headers={"X-CSRF-Token": csrf},
    )
    third = api_client.post(
        "/api/v1/admin/change-records/00000000-0000-0000-0000-000000000000/approve",
        headers={"X-CSRF-Token": csrf},
    )

    assert first.status_code == 404
    assert second.status_code == 404
    assert third.status_code == 429
    assert "Retry-After" in third.headers


def test_a_second_users_session_cannot_use_the_first_users_role(
    api_client: TestClient, db_session: Session
) -> None:
    """Two independent authenticated identities against the same shared
    test database — the second user's own session must reflect their
    own (unprivileged) role, never anything inherited from the first
    session, matching `tests/test_tracking/test_api.py`'s established
    two-`TestClient`-instances isolation pattern (a second `TestClient
    (app)` shares `api_client`'s `get_db` override, set globally on the
    `app` object, while keeping its own independent cookie jar)."""
    editor_client = TestClient(app)

    make_user(db_session, email="isolated-user@example-test.invalid", role=UserRole.USER)
    make_user(db_session, email="isolated-editor@example-test.invalid", role=UserRole.EDITOR)
    _login(api_client, "isolated-user@example-test.invalid")
    _login(editor_client, "isolated-editor@example-test.invalid")

    user_response = api_client.get("/api/v1/admin/dashboard")
    editor_response = editor_client.get("/api/v1/admin/dashboard")

    assert user_response.status_code == 403
    assert editor_response.status_code == 200
