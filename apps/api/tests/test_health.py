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
