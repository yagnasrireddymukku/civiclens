"""POST /api/v1/auth/register, /login, /refresh, /logout,
GET/PATCH /api/v1/auth/me — exercised against a real database via the
`api_client` fixture (docs/TESTING.md §3), including cookie-based auth
and the CSRF double-submit check end to end.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings


def test_register_sets_cookies_and_returns_the_user(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "newcomer@example-test.invalid", "password": "a-strong-password-1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "newcomer@example-test.invalid"
    assert body["user"]["role"] == "user"
    assert body["csrf_token"]

    settings = get_settings()
    assert settings.access_cookie_name in response.cookies
    assert settings.refresh_cookie_name in response.cookies
    assert settings.csrf_cookie_name in response.cookies


def test_register_rejects_a_duplicate_email(api_client: TestClient) -> None:
    api_client.post(
        "/api/v1/auth/register",
        json={"email": "dupe@example-test.invalid", "password": "a-strong-password-1"},
    )
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "dupe@example-test.invalid", "password": "a-different-password"},
    )
    assert response.status_code == 409


def test_register_rejects_a_too_short_password(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "shortpw@example-test.invalid", "password": "short"},
    )
    assert response.status_code == 422


def test_register_rejects_a_malformed_email(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "a-strong-password-1"},
    )
    assert response.status_code == 422


def test_login_succeeds_with_correct_credentials(api_client: TestClient) -> None:
    api_client.post(
        "/api/v1/auth/register",
        json={"email": "login-test@example-test.invalid", "password": "a-strong-password-1"},
    )
    api_client.cookies.clear()

    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "login-test@example-test.invalid", "password": "a-strong-password-1"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "login-test@example-test.invalid"


def test_login_rejects_wrong_password(api_client: TestClient) -> None:
    api_client.post(
        "/api/v1/auth/register",
        json={"email": "login-test-2@example-test.invalid", "password": "a-strong-password-1"},
    )
    api_client.cookies.clear()

    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "login-test-2@example-test.invalid", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_me_requires_authentication(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_the_authenticated_user(api_client: TestClient) -> None:
    api_client.post(
        "/api/v1/auth/register",
        json={"email": "me-test@example-test.invalid", "password": "a-strong-password-1"},
    )
    response = api_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "me-test@example-test.invalid"


def test_update_preferences_requires_csrf_token(api_client: TestClient) -> None:
    api_client.post(
        "/api/v1/auth/register",
        json={"email": "csrf-test@example-test.invalid", "password": "a-strong-password-1"},
    )
    response = api_client.patch("/api/v1/auth/me", json={"email_notifications_enabled": True})
    assert response.status_code == 403


def test_update_preferences_succeeds_with_a_valid_csrf_token(api_client: TestClient) -> None:
    register_response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "csrf-test-2@example-test.invalid", "password": "a-strong-password-1"},
    )
    csrf_token = register_response.json()["csrf_token"]

    response = api_client.patch(
        "/api/v1/auth/me",
        json={"email_notifications_enabled": True},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 200
    assert response.json()["email_notifications_enabled"] is True


def test_refresh_rotates_the_refresh_token_and_stays_authenticated(api_client: TestClient) -> None:
    api_client.post(
        "/api/v1/auth/register",
        json={"email": "refresh-test@example-test.invalid", "password": "a-strong-password-1"},
    )
    old_refresh_cookie = api_client.cookies.get(get_settings().refresh_cookie_name)

    response = api_client.post("/api/v1/auth/refresh")
    assert response.status_code == 200

    new_refresh_cookie = api_client.cookies.get(get_settings().refresh_cookie_name)
    assert new_refresh_cookie != old_refresh_cookie

    me_response = api_client.get("/api/v1/auth/me")
    assert me_response.status_code == 200


def test_refresh_without_a_refresh_cookie_is_unauthenticated(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_logout_requires_csrf_and_then_invalidates_the_session(
    api_client: TestClient, db_session: Session
) -> None:
    register_response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "logout-test@example-test.invalid", "password": "a-strong-password-1"},
    )
    csrf_token = register_response.json()["csrf_token"]

    no_csrf_response = api_client.post("/api/v1/auth/logout")
    assert no_csrf_response.status_code == 403

    logout_response = api_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout_response.status_code == 204

    refresh_response = api_client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401
