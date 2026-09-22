"""Fixture-loading itself is tested — docs/TESTING.md §5: "a broken
fixture can't silently pass every downstream test against empty data."
Mirrors tests/test_services/test_fixtures.py.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.jobs.fixtures import load_fixtures as load_job_fixtures
from app.schemes.fixtures import load_fixtures
from app.schemes.models import Scheme
from app.search.service import search_documents
from app.services.fixtures import load_fixtures as load_service_fixtures


def test_load_fixtures_creates_three_findable_published_schemes(db_session: Session) -> None:
    load_fixtures(db_session)

    pension = db_session.query(Scheme).filter_by(slug="test-civiclens-scheme-001").one()
    assert pension.name == "Test Old-Age Pension Scheme (Fixture)"
    assert len(pension.benefits) == 1
    assert len(pension.requirements) == 2
    assert len(pension.required_documents) == 1
    assert len(pension.application_methods) == 1

    scholarship = db_session.query(Scheme).filter_by(slug="test-civiclens-scheme-002").one()
    assert scholarship.name == "Test Merit Scholarship Scheme (Fixture)"

    linked = db_session.query(Scheme).filter_by(slug="test-civiclens-scheme-003").one()
    assert linked.name == "Test Income Support Scheme (Fixture)"
    assert len(linked.related_services) == 1
    assert linked.related_services[0].service.slug == "test-civiclens-linked-service-001"

    result = search_documents(db_session, q="Test Old-Age Pension", locale="en")
    assert result.total_count == 1
    assert result.rows[0].document.route == "/schemes/test-civiclens-scheme-001"


def test_load_fixtures_reuses_the_shared_fixture_geography_and_organization(
    db_session: Session,
) -> None:
    """Regression test for the exact bug found by hand in Phase 6/7
    (docs/DATABASE.md §9): seeding jobs, service, and scheme fixtures
    into the same database must not collide on the shared "Testland"
    state or "Test Recruitment Board — Not Real" organization's
    uniqueness constraints."""
    load_job_fixtures(db_session)
    load_service_fixtures(db_session)
    load_fixtures(db_session)  # must not raise


def test_load_fixtures_is_independently_runnable_without_service_fixtures(
    db_session: Session,
) -> None:
    """The service-linked scheme creates its own small Service fixture
    rather than depending on `app.services.fixtures` having run first —
    see app/schemes/fixtures.py's module docstring."""
    load_fixtures(db_session)  # must not raise, even without load_service_fixtures first


def test_load_fixtures_refuses_to_run_outside_local_or_test(db_session: Session) -> None:
    with patch("app.schemes.fixtures.get_settings") as mock_settings:
        mock_settings.return_value = Settings(app_env="production")
        with pytest.raises(RuntimeError, match="Refusing to load scheme fixtures"):
            load_fixtures(db_session)
