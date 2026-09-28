"""GET /api/v1/eligibility/criteria, POST /api/v1/eligibility/evaluate —
exercised against a real database via the `api_client` fixture, never
mocks, per docs/TESTING.md §3.
"""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.eligibility.enums import EligibilityAttribute, EligibilityOperator
from tests.test_eligibility._helpers import (
    make_condition,
    make_job,
    make_organization,
    make_rule,
    make_scheme,
    make_source,
    make_state,
)


def test_get_criteria_returns_questions_for_supported_entity(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(db_session, source=source, job=job)
    make_condition(db_session, rule)

    response = api_client.get(
        "/api/v1/eligibility/criteria", params={"entity_type": "JOB", "entity_slug": job.slug}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["rule_version"] == 1
    assert len(body["criteria"]) == 1
    assert body["criteria"][0]["attribute"] == "AGE"
    assert body["source"]["title"]
    # No submitted-answer concept exists at all on this read-only
    # endpoint, so there is nothing to leak — asserted structurally by
    # the schema itself rather than by inspecting the response body.


def test_get_criteria_reports_unsupported_when_no_rule_exists(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)

    response = api_client.get(
        "/api/v1/eligibility/criteria", params={"entity_type": "SCHEME", "entity_slug": scheme.slug}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is False
    assert body["criteria"] == []
    assert body["rule_id"] is None


def test_get_criteria_returns_404_for_unknown_entity(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/eligibility/criteria",
        params={"entity_type": "JOB", "entity_slug": "no-such-job"},
    )
    assert response.status_code == 404


def test_evaluate_returns_eligible_when_all_conditions_pass(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(db_session, source=source, job=job)
    make_condition(db_session, rule)  # AGE BETWEEN 18-35

    response = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"entity_type": "JOB", "entity_slug": job.slug, "answers": {"age": 25}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["outcome"] == "ELIGIBLE"
    assert body["missing_attributes"] == []
    assert body["failed_attributes"] == []
    assert body["rule_id"] == str(rule.id)
    assert body["source"]["organization"]


def test_evaluate_returns_not_eligible_on_a_failed_condition(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(db_session, source=source, job=job)
    make_condition(db_session, rule)  # AGE BETWEEN 18-35

    response = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"entity_type": "JOB", "entity_slug": job.slug, "answers": {"age": 90}},
    )

    body = response.json()
    assert body["outcome"] == "NOT_ELIGIBLE"
    assert body["failed_attributes"] == ["AGE"]


def test_evaluate_returns_incomplete_when_answer_missing(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    job = make_job(db_session, organization=organization, state=state, source=source)
    rule = make_rule(db_session, source=source, job=job)
    make_condition(db_session, rule)  # AGE BETWEEN 18-35

    response = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"entity_type": "JOB", "entity_slug": job.slug, "answers": {}},
    )

    body = response.json()
    assert body["outcome"] == "INCOMPLETE"
    assert body["missing_attributes"] == ["AGE"]


def test_evaluate_reports_unsupported_when_no_rule_exists(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)

    response = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"entity_type": "SCHEME", "entity_slug": scheme.slug, "answers": {}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is False
    assert body["outcome"] is None
    assert body["message"]


def test_evaluate_returns_404_for_unknown_entity(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"entity_type": "SERVICE", "entity_slug": "no-such-service", "answers": {}},
    )
    assert response.status_code == 404


def test_evaluate_rejects_out_of_range_age(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"entity_type": "JOB", "entity_slug": "irrelevant", "answers": {"age": 999}},
    )
    assert response.status_code == 422


def test_evaluate_rejects_unknown_answer_field(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={
            "entity_type": "JOB",
            "entity_slug": "irrelevant",
            "answers": {"unexpected_field": "value"},
        },
    )
    assert response.status_code == 422


def test_evaluate_with_between_condition_boundary_via_api(
    api_client: TestClient, db_session: Session
) -> None:
    state = make_state(db_session)
    source = make_source(db_session)
    organization = make_organization(db_session, state)
    scheme = make_scheme(db_session, organization=organization, source=source)
    rule = make_rule(db_session, source=source, scheme=scheme)
    make_condition(
        db_session,
        rule,
        attribute=EligibilityAttribute.ACADEMIC_PERCENTAGE,
        operator=EligibilityOperator.GTE,
        numeric_value=Decimal("60.00"),
        numeric_value_max=None,
        description="At least 60%.",
    )

    response = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={
            "entity_type": "SCHEME",
            "entity_slug": scheme.slug,
            "answers": {"academic_percentage": "60.00"},
        },
    )

    assert response.json()["outcome"] == "ELIGIBLE"
