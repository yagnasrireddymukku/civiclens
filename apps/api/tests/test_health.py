from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "civiclens-api"
    assert "version" in body
    assert "timestamp" in body


def test_health_response_shape_matches_shared_type(client: TestClient) -> None:
    # Mirrors packages/types' HealthStatus — see docs/API.md §10 on keeping
    # the frontend/backend contract in sync without hand-copying either way.
    body = client.get("/api/v1/health").json()
    assert set(body.keys()) == {"status", "service", "version", "timestamp"}


def test_health_response_includes_request_id_header(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert "X-Request-ID" in response.headers


def test_app_boots_and_liveness_works_without_a_reachable_database(client: TestClient) -> None:
    """The `client` fixture already imports and boots the whole app
    against the default DATABASE_URL (app.core.config.Settings), which
    points at a host with no real Postgres server in this environment.
    `app.core.db.session.get_engine()` is lazy — constructing an Engine
    does not connect — so this must still succeed. If a future change
    made engine creation eager, this test module would fail to collect
    at all, not just this one assertion.

    See docs/ROADMAP.md Phase 3: "the application must remain capable of
    starting in a local environment without requiring a production
    database."
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
