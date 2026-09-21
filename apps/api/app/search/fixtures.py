"""Synthetic search fixtures — for local development and automated tests
only. Never real government data (docs/DATA_GOVERNANCE.md §7, this
phase's §14).

Naming follows docs/TESTING.md §15 exactly: fake state code "ZZ"/state
name "Testland", organization "Test Board — Not Real", `.invalid` source
URLs, entity names carrying an unambiguous "(Fixture)"/"Not Real" marker.
`load_fixtures` refuses to run outside local/test environments — a second
line of defense beyond "don't call this in production code," matching
the same pattern docs/TESTING.md §15 requires of the fixture-loading
utility.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.geography.enums import StateStatus
from app.geography.models import District, State
from app.search.service import upsert_search_document
from app.sources.enums import VerificationStatus
from app.sources.models import Source

_ALLOWED_ENVIRONMENTS = ("local", "test")


@dataclass(frozen=True)
class FixtureDocument:
    entity_type: str
    entity_id: uuid.UUID
    locale: str
    title: str
    summary: str
    searchable_text: str
    route: str
    category: str
    status: str
    verification_status: VerificationStatus


def _fixture_state() -> State:
    return State(name="Testland", code="ZZ", slug="testland", status=StateStatus.PLANNED)


def _fixture_district(state: State) -> District:
    return District(state_id=state.id, name="Sampleburg", code="SB", slug="sampleburg")


def _fixture_source() -> Source:
    return Source(
        url="https://example-test.invalid/notice/search-fixtures",
        title="Test Notice — Not Real",
        organization="Test Board — Not Real",
        source_type="test-fixture",
        retrieved_date=datetime.date(2026, 1, 1),
    )


_FIXTURE_DOCUMENTS: tuple[FixtureDocument, ...] = (
    FixtureDocument(
        entity_type="TEST_JOB",
        entity_id=uuid.uuid4(),
        locale="en",
        title="Sample Recruitment Notice (Fixture)",
        summary="A fictional recruitment notice used only to exercise search — not a real job.",
        searchable_text="test fixture recruitment notice fictional example clerk grade II",
        route="/jobs/test-job-001",
        category="recruitment",
        status="open",
        verification_status=VerificationStatus.VERIFIED,
    ),
    FixtureDocument(
        entity_type="TEST_SERVICE",
        entity_id=uuid.uuid4(),
        locale="en",
        title="Test Certificate Service (Fixture)",
        summary="A fictional government service used only to exercise search — not a real service.",
        searchable_text="test fixture certificate issuance service fictional example",
        route="/services/test-service-001",
        category="certificate",
        status="available",
        verification_status=VerificationStatus.VERIFIED,
    ),
    FixtureDocument(
        entity_type="TEST_SCHEME",
        entity_id=uuid.uuid4(),
        locale="en",
        title="Test Assistance Scheme — Not Real",
        summary="A fictional scheme used only to exercise search — needs-review status on purpose.",
        searchable_text="test fixture assistance scheme fictional example passport support",
        route="/schemes/test-scheme-001",
        category="assistance",
        status="active",
        verification_status=VerificationStatus.NEEDS_REVIEW,
    ),
    FixtureDocument(
        entity_type="TEST_SCHEME",
        entity_id=uuid.uuid4(),
        locale="te",
        title="పరీక్ష సహాయ పథకం — నిజం కాదు",
        summary="శోధనను పరీక్షించడానికి మాత్రమే ఉపయోగించే ఫిక్చర్ పథకం — నిజమైనది కాదు.",
        searchable_text="పరీక్ష ఫిక్చర్ సహాయ పథకం ఉదాహరణ",
        route="/schemes/test-scheme-001",
        category="assistance",
        status="active",
        verification_status=VerificationStatus.VERIFIED,
    ),
)


def load_fixtures(session: Session) -> None:
    """Inserts a small, fixed set of synthetic search documents (plus
    the fictional state/district/source rows they reference). Refuses
    to run unless `APP_ENV` is "local" or "test" — see module docstring.
    """
    settings = get_settings()
    if settings.app_env not in _ALLOWED_ENVIRONMENTS:
        raise RuntimeError(
            f"Refusing to load search fixtures: APP_ENV={settings.app_env!r} is not one of "
            f"{_ALLOWED_ENVIRONMENTS}. Fixtures must never reach a staging/production database."
        )

    state = _fixture_state()
    session.add(state)
    session.flush()

    district = _fixture_district(state)
    session.add(district)

    source = _fixture_source()
    session.add(source)
    session.flush()

    for fixture in _FIXTURE_DOCUMENTS:
        upsert_search_document(
            session,
            entity_type=fixture.entity_type,
            entity_id=fixture.entity_id,
            locale=fixture.locale,
            title=fixture.title,
            summary=fixture.summary,
            searchable_text=fixture.searchable_text,
            route=fixture.route,
            state_id=state.id,
            district_id=district.id,
            category=fixture.category,
            status=fixture.status,
            source_id=source.id,
            verification_status=fixture.verification_status,
            last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
        )

    session.commit()
