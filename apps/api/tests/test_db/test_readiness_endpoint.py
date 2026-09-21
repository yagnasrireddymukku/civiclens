"""GET /api/v1/health/ready — exercised against a real database (ready)
and a real-but-unreachable one (not ready), never a mock, per
docs/TESTING.md §3.
"""

import pytest
from sqlalchemy import Engine, create_engine
from starlette.testclient import TestClient

import app.core.db.session as db_session_module
from app.main import app


def test_readiness_is_ready_when_database_is_reachable(
    migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(db_session_module, "get_engine", lambda: migrated_engine)

    client = TestClient(app)
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readiness_is_not_ready_when_database_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A real Engine, pointed at a port nothing is listening on — a genuine
    # connection failure, not a simulated/mocked one.
    unreachable_engine = create_engine(
        "postgresql+psycopg://baduser:badpass@127.0.0.1:1/nonexistent?connect_timeout=1",
        future=True,
    )
    monkeypatch.setattr(db_session_module, "get_engine", lambda: unreachable_engine)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/ready")

        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "NOT_READY"
    finally:
        unreachable_engine.dispose()
