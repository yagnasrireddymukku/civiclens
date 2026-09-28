"""GET /api/v1/notifications, POST /api/v1/notifications/{id}/read,
POST /api/v1/notifications/read-all — exercised through the real auth
flow (register -> cookies), matching `tests/test_tracking/test_api.py`'s
established convention (docs/TESTING.md §3, "no public endpoint that
lets unauthenticated users create or read arbitrary user data").
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.users.models import User
from tests.test_notifications._helpers import make_notification


def _register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "a-strong-password-1"}
    )
    assert response.status_code == 201
    return response.json()["csrf_token"]


def _user_id_by_email(db_session: Session, email: str):
    return db_session.query(User).filter_by(email=email).one().id


def test_notifications_requires_authentication(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/notifications")
    assert response.status_code == 401


def test_list_notifications_for_the_authenticated_user(
    api_client: TestClient, db_session: Session
) -> None:
    _register(api_client, "inbox-owner@example-test.invalid")
    user_id = _user_id_by_email(db_session, "inbox-owner@example-test.invalid")
    make_notification(db_session, user_id=user_id, dedup_key="A")
    make_notification(db_session, user_id=user_id, dedup_key="B")

    response = api_client.get("/api/v1/notifications")

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    assert body["unread_count"] == 2
    assert body["pagination"]["total_count"] == 2


def test_list_notifications_paginates(api_client: TestClient, db_session: Session) -> None:
    _register(api_client, "paginator@example-test.invalid")
    user_id = _user_id_by_email(db_session, "paginator@example-test.invalid")
    for i in range(3):
        make_notification(db_session, user_id=user_id, dedup_key=f"KEY-{i}")

    response = api_client.get("/api/v1/notifications", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    assert body["pagination"]["total_count"] == 3


def test_mark_read_requires_csrf_token(api_client: TestClient, db_session: Session) -> None:
    _register(api_client, "csrf-notif@example-test.invalid")
    user_id = _user_id_by_email(db_session, "csrf-notif@example-test.invalid")
    notification = make_notification(db_session, user_id=user_id)

    response = api_client.post(f"/api/v1/notifications/{notification.id}/read")
    assert response.status_code == 403


def test_mark_read_updates_read_state(api_client: TestClient, db_session: Session) -> None:
    csrf_token = _register(api_client, "reader@example-test.invalid")
    user_id = _user_id_by_email(db_session, "reader@example-test.invalid")
    notification = make_notification(db_session, user_id=user_id)

    response = api_client.post(
        f"/api/v1/notifications/{notification.id}/read", headers={"X-CSRF-Token": csrf_token}
    )

    assert response.status_code == 200
    assert response.json()["read_at"] is not None

    list_response = api_client.get("/api/v1/notifications")
    assert list_response.json()["unread_count"] == 0


def test_mark_read_on_a_nonexistent_notification_404s(api_client: TestClient) -> None:
    csrf_token = _register(api_client, "reader2@example-test.invalid")
    response = api_client.post(
        "/api/v1/notifications/00000000-0000-0000-0000-000000000000/read",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 404


def test_cannot_mark_another_users_notification_read(
    api_client: TestClient, db_session: Session
) -> None:
    _register(api_client, "notif-owner@example-test.invalid")
    owner_id = _user_id_by_email(db_session, "notif-owner@example-test.invalid")
    notification = make_notification(db_session, user_id=owner_id)

    attacker_client = TestClient(app)
    attacker_csrf = _register(attacker_client, "notif-attacker@example-test.invalid")

    response = attacker_client.post(
        f"/api/v1/notifications/{notification.id}/read",
        headers={"X-CSRF-Token": attacker_csrf},
    )
    assert response.status_code == 404

    owner_list = api_client.get("/api/v1/notifications")
    assert owner_list.json()["unread_count"] == 1


def test_mark_all_read_requires_csrf_token(api_client: TestClient) -> None:
    _register(api_client, "markall-csrf@example-test.invalid")
    response = api_client.post("/api/v1/notifications/read-all")
    assert response.status_code == 403


def test_mark_all_read_only_affects_the_calling_user(
    api_client: TestClient, db_session: Session
) -> None:
    csrf_token = _register(api_client, "markall-owner@example-test.invalid")
    owner_id = _user_id_by_email(db_session, "markall-owner@example-test.invalid")
    make_notification(db_session, user_id=owner_id, dedup_key="A")
    make_notification(db_session, user_id=owner_id, dedup_key="B")

    attacker_client = TestClient(app)
    _register(attacker_client, "markall-attacker@example-test.invalid")
    attacker_id = _user_id_by_email(db_session, "markall-attacker@example-test.invalid")
    make_notification(db_session, user_id=attacker_id, dedup_key="C")

    response = api_client.post(
        "/api/v1/notifications/read-all", headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 204

    owner_list = api_client.get("/api/v1/notifications")
    assert owner_list.json()["unread_count"] == 0

    attacker_list = attacker_client.get("/api/v1/notifications")
    assert attacker_list.json()["unread_count"] == 1
