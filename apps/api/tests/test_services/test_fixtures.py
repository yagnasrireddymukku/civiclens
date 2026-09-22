"""Fixture-loading itself is tested — docs/TESTING.md §5: "a broken
fixture can't silently pass every downstream test against empty data."
Mirrors tests/test_jobs/test_fixtures.py.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.jobs.fixtures import load_fixtures as load_job_fixtures
from app.search.service import search_documents
from app.services.fixtures import load_fixtures
from app.services.models import Service


def test_load_fixtures_creates_a_findable_published_service(db_session: Session) -> None:
    load_fixtures(db_session)

    service = db_session.query(Service).filter_by(slug="test-civiclens-service-001").one()
    assert service.name == "Test Income Certificate Issuance (Fixture)"
    assert len(service.requirements) == 2
    assert len(service.required_documents) == 3
    assert len(service.application_methods) == 2

    result = search_documents(db_session, q="Test Income Certificate", locale="en")
    assert result.total_count == 1
    assert result.rows[0].document.route == "/services/test-civiclens-service-001"


def test_load_fixtures_reuses_the_shared_fixture_geography_and_organization(
    db_session: Session,
) -> None:
    """Regression test for the exact bug found by hand (docs/DATABASE.md
    §9): seeding both jobs and service fixtures into the same database
    must not collide on the shared "Testland" state or "Test Recruitment
    Board — Not Real" organization's uniqueness constraints."""
    load_job_fixtures(db_session)
    load_fixtures(db_session)  # must not raise


def test_load_fixtures_refuses_to_run_outside_local_or_test(db_session: Session) -> None:
    with patch("app.services.fixtures.get_settings") as mock_settings:
        mock_settings.return_value = Settings(app_env="production")
        with pytest.raises(RuntimeError, match="Refusing to load service fixtures"):
            load_fixtures(db_session)
