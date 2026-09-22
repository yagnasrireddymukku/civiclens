"""Fixture-loading itself is tested — docs/TESTING.md §5: "a broken
fixture can't silently pass every downstream test against empty data."
"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.jobs.fixtures import load_fixtures
from app.jobs.models import Job
from app.search.service import search_documents


def test_load_fixtures_creates_a_findable_published_job(db_session: Session) -> None:
    load_fixtures(db_session)

    job = db_session.query(Job).filter_by(slug="test-civiclens-job-001").one()
    assert job.title == "Test Civic Clerk Recruitment (Fixture)"
    assert len(job.notifications) == 1
    assert len(job.notifications[0].vacancies) == 2

    result = search_documents(db_session, q="Test Civic Clerk", locale="en")
    assert result.total_count == 1
    assert result.rows[0].document.route == "/jobs/test-civiclens-job-001"


def test_load_fixtures_refuses_to_run_outside_local_or_test(db_session: Session) -> None:
    with patch("app.jobs.fixtures.get_settings") as mock_settings:
        mock_settings.return_value = Settings(app_env="production")
        with pytest.raises(RuntimeError, match="Refusing to load job fixtures"):
            load_fixtures(db_session)
