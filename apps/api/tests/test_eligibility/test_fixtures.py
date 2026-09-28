"""Tests for app/eligibility/fixtures.py — mirrors
tests/test_documents/test_fixtures.py's pattern. Fixture loading is not
idempotent (matches every other domain's established, intentional
convention — see docs/DATABASE.md's Phase 10 note), so this only tests a
single load, not a repeated one.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.eligibility.fixtures import load_fixtures
from app.eligibility.models import EligibilityRule
from app.jobs.models import Job
from app.schemes.models import Scheme
from app.services.models import Service


def test_load_fixtures_creates_one_rule_per_entity_type(db_session: Session) -> None:
    load_fixtures(db_session)

    job = db_session.query(Job).filter_by(slug="test-civiclens-eligibility-job-001").one()
    scheme = db_session.query(Scheme).filter_by(slug="test-civiclens-eligibility-scheme-001").one()
    service = (
        db_session.query(Service).filter_by(slug="test-civiclens-eligibility-service-001").one()
    )

    job_rule = db_session.query(EligibilityRule).filter_by(job_id=job.id).one()
    scheme_rule = db_session.query(EligibilityRule).filter_by(scheme_id=scheme.id).one()
    service_rule = db_session.query(EligibilityRule).filter_by(service_id=service.id).one()

    assert len(job_rule.conditions) == 2
    assert len(scheme_rule.conditions) == 2
    assert len(service_rule.conditions) == 2


def test_load_fixtures_refuses_outside_local_or_test(db_session: Session) -> None:
    with patch("app.eligibility.fixtures.get_settings") as mock_settings:
        mock_settings.return_value = Settings(app_env="production")
        with pytest.raises(RuntimeError, match="Refusing to load eligibility fixtures"):
            load_fixtures(db_session)
