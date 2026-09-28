"""GET /api/v1/ai/health, POST /api/v1/ai/ask, POST
/api/v1/ai/explain-eligibility — exercised against a real database via
the `api_client` fixture, never mocks for the DB layer (docs/TESTING.md
§3). Provider calls are faked via monkeypatching
`app.api.v1.ai.get_llm_provider`/`get_embedding_provider` (the names
actually bound in the router module, not the origin module — a plain
`from X import Y` copies the reference at import time).
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.enums import AIEntityType
from app.ai.indexing import index_one
from app.jobs.service import sync_job_search_index
from tests.test_ai._helpers import FakeEmbeddingProvider, FakeLLMProvider
from tests.test_documents._helpers import make_organization, make_source, make_state
from tests.test_eligibility._helpers import make_condition, make_rule
from tests.test_jobs._helpers import make_job


def _sync(coro):
    return asyncio.run(coro)


def test_ai_health_reports_unconfigured_providers_by_default(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/ai/health")
    assert response.status_code == 200
    body = response.json()
    assert body["llm_configured"] is False
    assert body["embedding_configured"] is False


def test_ask_returns_provider_unavailable_when_ai_is_not_configured(
    api_client: TestClient,
) -> None:
    response = api_client.post("/api/v1/ai/ask", json={"question": "What jobs are available?"})
    assert response.status_code == 200
    body = response.json()
    assert body["grounding_status"] == "PROVIDER_UNAVAILABLE"
    assert body["answer"] is None
    assert body["disclaimer"]


def test_ask_rejects_a_too_short_question(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/ai/ask", json={"question": "hi"})
    assert response.status_code == 422


def test_ask_rejects_a_too_long_question(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/ai/ask", json={"question": "a" * 501})
    assert response.status_code == 422


def test_ask_rejects_an_invalid_locale(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/ai/ask", json={"question": "What jobs are available?", "locale": "fr"}
    )
    assert response.status_code == 422


def test_ask_rejects_unknown_fields(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/ai/ask", json={"question": "What jobs are available?", "unexpected": "value"}
    )
    assert response.status_code == 422


def test_ask_returns_grounded_answer_with_a_configured_fake_provider(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(
        db_session,
        organization=organization,
        state=state,
        source=source,
        title="Test Junior Assistant Recruitment (Fixture)",
    )
    sync_job_search_index(db_session, job)
    embedding = FakeEmbeddingProvider(dimensions=8)
    _sync(
        index_one(
            db_session,
            entity_type=AIEntityType.JOB,
            entity_id=job.id,
            locale="en",
            embedding_provider=embedding,
        )
    )
    llm = FakeLLMProvider('{"answer": "The role is open.", "citation_ids": [1], "grounded": true}')

    monkeypatch.setattr("app.api.v1.ai.get_llm_provider", lambda: llm)
    monkeypatch.setattr("app.api.v1.ai.get_embedding_provider", lambda: embedding)

    response = api_client.post("/api/v1/ai/ask", json={"question": "Junior Assistant Recruitment"})

    assert response.status_code == 200
    body = response.json()
    assert body["grounding_status"] == "GROUNDED"
    assert body["answer"] == "The role is open."
    assert len(body["citations"]) == 1
    assert body["citations"][0]["route"] == f"/jobs/{job.slug}"
    assert "source" in body["citations"][0]


def test_explain_eligibility_returns_404_shaped_not_supported_for_unknown_entity(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/api/v1/ai/explain-eligibility",
        json={"entity_type": "JOB", "entity_slug": "does-not-exist", "answers": {}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ENTITY_NOT_FOUND"


def test_explain_eligibility_without_llm_uses_template(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(db_session, source=source, job=job)
    make_condition(db_session, rule)

    response = api_client.post(
        "/api/v1/ai/explain-eligibility",
        json={
            "entity_type": "JOB",
            "entity_slug": job.slug,
            "answers": {"age": 25, "residence_state_code": "ZZ"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "EXPLAINED"
    assert body["outcome"] == "ELIGIBLE"
    assert body["rule_id"] == str(rule.id)
    assert body["explanation"]


def test_explain_eligibility_rejects_unknown_fields(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/ai/explain-eligibility",
        json={"entity_type": "JOB", "entity_slug": "x", "answers": {}, "unexpected": "value"},
    )
    assert response.status_code == 422


def test_ai_rate_limit_returns_429_after_the_configured_number_of_requests(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import Settings

    low_limit_settings = Settings(ai_rate_limit_requests=2, ai_rate_limit_window_seconds=60.0)
    monkeypatch.setattr("app.ai.rate_limit.get_settings", lambda: low_limit_settings)
    # Isolate this test's IP bucket from any other test's accumulated hits.
    from app.ai.rate_limit import _hits

    _hits.clear()

    first = api_client.post("/api/v1/ai/ask", json={"question": "What jobs are available?"})
    second = api_client.post("/api/v1/ai/ask", json={"question": "What jobs are available?"})
    third = api_client.post("/api/v1/ai/ask", json={"question": "What jobs are available?"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert "Retry-After" in third.headers
    assert third.json()["error"]["code"] == "RATE_LIMITED"
