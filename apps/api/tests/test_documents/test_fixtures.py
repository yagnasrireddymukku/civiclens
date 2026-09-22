"""Fixture-loading itself is tested — docs/TESTING.md §5: "a broken
fixture can't silently pass every downstream test against empty data."
Mirrors tests/test_schemes/test_fixtures.py.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.documents.fixtures import load_fixtures
from app.documents.models import CivicDocument
from app.documents.service import get_required_by
from app.jobs.fixtures import load_fixtures as load_job_fixtures
from app.schemes.fixtures import load_fixtures as load_scheme_fixtures
from app.search.service import search_documents


def test_load_fixtures_creates_two_findable_published_documents(db_session: Session) -> None:
    load_fixtures(db_session)

    residence = db_session.query(CivicDocument).filter_by(slug="test-civiclens-document-001").one()
    assert residence.name == "Test Residence Certificate (Fixture)"
    assert len(residence.application_methods) == 1

    income = db_session.query(CivicDocument).filter_by(slug="test-civiclens-document-002").one()
    assert income.name == "Test Income Certificate (Fixture)"
    assert len(income.requirements) == 2
    assert len(income.supporting_documents) == 2
    assert len(income.application_methods) == 1
    assert income.service is not None
    assert income.service.slug == "test-civiclens-linked-service-002"

    # The recursive supporting-document link (this phase's §11).
    residence_link = next(
        s for s in income.supporting_documents if s.name == "Residence Certificate (Fixture)"
    )
    assert residence_link.civic_document_id == residence.id

    result = search_documents(db_session, q="Test Income Certificate", locale="en")
    assert result.total_count == 1
    assert result.rows[0].document.route == "/documents/test-civiclens-document-002"


def test_load_fixtures_creates_the_required_by_reverse_link(db_session: Session) -> None:
    """The end-to-end "required by" demonstration (this phase's
    §14/§22): a small fixture Scheme's `SchemeRequiredDocument` row
    points its `civic_document_id` at the Income Certificate."""
    load_fixtures(db_session)

    income = db_session.query(CivicDocument).filter_by(slug="test-civiclens-document-002").one()
    required_by = get_required_by(db_session, income.id)

    assert any(
        entry.entity_type == "scheme" and entry.slug == "test-civiclens-scheme-004"
        for entry in required_by
    )


def test_load_fixtures_reuses_the_shared_fixture_geography_and_organization(
    db_session: Session,
) -> None:
    """Regression test for the exact bug found by hand in Phase 6/7
    (docs/DATABASE.md §9): seeding jobs, scheme, and document fixtures
    into the same database must not collide on the shared "Testland"
    state or "Test Recruitment Board — Not Real" organization's
    uniqueness constraints."""
    load_job_fixtures(db_session)
    load_scheme_fixtures(db_session)
    load_fixtures(db_session)  # must not raise


def test_load_fixtures_is_independently_runnable_without_other_domains(
    db_session: Session,
) -> None:
    """The linked Service and Scheme create their own small fixtures
    rather than depending on `app.services.fixtures`/
    `app.schemes.fixtures` having run first — see
    app/documents/fixtures.py's module docstring."""
    load_fixtures(db_session)  # must not raise, even without the other domains' fixtures first


def test_load_fixtures_refuses_to_run_outside_local_or_test(db_session: Session) -> None:
    with patch("app.documents.fixtures.get_settings") as mock_settings:
        mock_settings.return_value = Settings(app_env="production")
        with pytest.raises(RuntimeError, match="Refusing to load document fixtures"):
            load_fixtures(db_session)
