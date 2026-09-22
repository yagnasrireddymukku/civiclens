"""Search service tests — run against a real PostgreSQL with `pg_trgm`
(see tests/conftest.py's `db_session` fixture, shared by every test
package). Fixture data is unambiguously fictional
(docs/DATA_GOVERNANCE.md §7, docs/TESTING.md §15).
"""

import datetime
import uuid

import pytest
from sqlalchemy.orm import Session

from app.geography.enums import StateStatus
from app.geography.models import State
from app.search.enums import SearchSortOption
from app.search.service import (
    TRIGRAM_SIMILARITY_THRESHOLD,
    remove_search_document,
    search_documents,
    upsert_search_document,
)
from app.sources.enums import VerificationStatus
from app.sources.models import Source


def make_source(session: Session, **overrides) -> Source:
    defaults = dict(
        url="https://example-test.invalid/notice/search",
        title="Test Notice — Not Real",
        organization="Test Board — Not Real",
        source_type="test-fixture",
        retrieved_date=datetime.date(2026, 1, 1),
    )
    defaults.update(overrides)
    source = Source(**defaults)
    session.add(source)
    session.flush()
    return source


def index_document(session: Session, source: Source, **overrides) -> uuid.UUID:
    entity_id = overrides.pop("entity_id", uuid.uuid4())
    defaults = dict(
        entity_type="TEST_JOB",
        entity_id=entity_id,
        locale="en",
        title="Sample Recruitment Notice (Fixture)",
        summary="A fictional notice used only to exercise search.",
        searchable_text="fictional example clerk grade recruitment",
        route="/jobs/test-job-001",
        source_id=source.id,
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )
    defaults.update(overrides)
    upsert_search_document(session, **defaults)
    return entity_id


def test_upsert_refuses_to_index_unverified_documents(db_session: Session) -> None:
    source = make_source(db_session)
    with pytest.raises(ValueError, match="Refusing to index"):
        upsert_search_document(
            db_session,
            entity_type="TEST_JOB",
            entity_id=uuid.uuid4(),
            locale="en",
            title="Should not be indexed",
            source_id=source.id,
            verification_status=VerificationStatus.UNVERIFIED,
        )


def test_exact_keyword_match_is_found(db_session: Session) -> None:
    source = make_source(db_session)
    index_document(db_session, source, title="Test Passport Renewal Notice (Fixture)")

    result = search_documents(db_session, q="passport", locale="en")

    assert result.total_count == 1
    assert result.fuzzy_fallback_used is False
    assert result.rows[0].document.title == "Test Passport Renewal Notice (Fixture)"


def test_typo_falls_back_to_trigram_similarity(db_session: Session) -> None:
    """The exact scenario docs/SEARCH.md §5 and this phase's §9 name:
    a misspelled query still surfaces the intended fictional result."""
    source = make_source(db_session)
    index_document(db_session, source, title="Test Passport Renewal Notice (Fixture)")

    result = search_documents(db_session, q="pasport", locale="en")

    assert result.fuzzy_fallback_used is True
    assert result.total_count == 1
    assert result.rows[0].document.title == "Test Passport Renewal Notice (Fixture)"


def test_unrelated_fuzzy_query_returns_no_results(db_session: Session) -> None:
    """Guards against the threshold being so loose that unrelated
    results dominate (this phase's §9)."""
    source = make_source(db_session)
    index_document(db_session, source, title="Test Passport Renewal Notice (Fixture)")

    result = search_documents(db_session, q="zzyyxx unrelated gibberish", locale="en")

    assert result.total_count == 0
    assert result.rows == []


def test_title_ranks_above_description_only_match(db_session: Session) -> None:
    source = make_source(db_session)
    index_document(
        db_session,
        source,
        entity_id=uuid.uuid4(),
        title="Test Certificate Notice (Fixture)",
        searchable_text="mentions scholarship only in passing",
    )
    index_document(
        db_session,
        source,
        entity_id=uuid.uuid4(),
        title="Test Scholarship Notice (Fixture)",
        searchable_text="a fictional scholarship scheme",
    )

    result = search_documents(db_session, q="scholarship", locale="en")

    assert result.total_count == 2
    assert result.rows[0].document.title == "Test Scholarship Notice (Fixture)"


def test_filters_are_applied_as_and_conditions(db_session: Session) -> None:
    source = make_source(db_session)
    state = State(name="Testland", code="ZZ", slug="testland", status=StateStatus.PLANNED)
    db_session.add(state)
    db_session.flush()

    index_document(
        db_session,
        source,
        entity_id=uuid.uuid4(),
        title="Test Job In Testland (Fixture)",
        category="recruitment",
        state_id=state.id,
    )
    index_document(
        db_session,
        source,
        entity_id=uuid.uuid4(),
        title="Test Job Elsewhere (Fixture)",
        category="recruitment",
        state_id=None,
    )

    result = search_documents(
        db_session, q="test job", locale="en", state_id=state.id, category="recruitment"
    )

    assert result.total_count == 1
    assert result.rows[0].document.title == "Test Job In Testland (Fixture)"


def test_empty_query_is_a_filters_only_browse_ordered_by_recency(
    db_session: Session,
) -> None:
    source = make_source(db_session)
    index_document(
        db_session,
        source,
        entity_id=uuid.uuid4(),
        title="Older Fixture Notice",
        last_verified_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    index_document(
        db_session,
        source,
        entity_id=uuid.uuid4(),
        title="Newer Fixture Notice",
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )

    result = search_documents(db_session, q="", locale="en")

    assert result.total_count == 2
    assert result.rows[0].document.title == "Newer Fixture Notice"


def test_pagination_is_bounded_and_reports_total_count(db_session: Session) -> None:
    source = make_source(db_session)
    for index in range(5):
        index_document(
            db_session,
            source,
            entity_id=uuid.uuid4(),
            title=f"Test Fixture Notice {index}",
        )

    result = search_documents(db_session, q="fixture", locale="en", page=1, page_size=2)

    assert result.total_count == 5
    assert len(result.rows) == 2


def test_source_and_verification_metadata_survive_into_results(db_session: Session) -> None:
    source = make_source(db_session, organization="Test Board — Not Real")
    index_document(
        db_session,
        source,
        title="Test Fixture With Provenance",
        verification_status=VerificationStatus.NEEDS_REVIEW,
    )

    result = search_documents(db_session, q="provenance", locale="en")

    assert result.total_count == 1
    row = result.rows[0]
    assert row.source.organization == "Test Board — Not Real"
    assert row.document.verification_status == VerificationStatus.NEEDS_REVIEW
    assert row.document.last_verified_at is not None


def test_locale_scopes_results_to_the_matching_language(db_session: Session) -> None:
    source = make_source(db_session)
    index_document(
        db_session,
        source,
        entity_id=uuid.uuid4(),
        locale="en",
        title="Test English Fixture Notice",
        searchable_text="fixture",
    )
    index_document(
        db_session,
        source,
        entity_id=uuid.uuid4(),
        locale="te",
        title="పరీక్ష ఫిక్చర్ నోటీసు",
        searchable_text="fixture",
    )

    en_result = search_documents(db_session, q="fixture", locale="en")
    te_result = search_documents(db_session, q="ఫిక్చర్", locale="te")

    assert en_result.total_count == 1
    assert en_result.rows[0].document.locale == "en"
    assert te_result.total_count == 1
    assert te_result.rows[0].document.locale == "te"


def test_remove_search_document_deletes_the_indexed_row(db_session: Session) -> None:
    source = make_source(db_session)
    entity_id = index_document(db_session, source, title="Test Fixture To Remove")

    remove_search_document(db_session, entity_type="TEST_JOB", entity_id=entity_id)
    db_session.flush()

    result = search_documents(db_session, q="fixture", locale="en")
    assert result.total_count == 0


def test_query_string_is_not_vulnerable_to_sql_injection(db_session: Session) -> None:
    """A hostile-looking query must behave as an ordinary (non-matching)
    search term, never alter query structure or error — proves
    parameterization, not string interpolation (this phase's §7/§22)."""
    source = make_source(db_session)
    index_document(db_session, source, title="Test Fixture Notice")

    hostile_query = "'; DROP TABLE search_documents; --"
    result = search_documents(db_session, q=hostile_query, locale="en")

    assert result.total_count == 0
    # The table must still exist and be queryable afterward.
    follow_up = search_documents(db_session, q="fixture", locale="en")
    assert follow_up.total_count == 1


def test_sort_by_last_verified_overrides_relevance_ordering(db_session: Session) -> None:
    source = make_source(db_session)
    index_document(
        db_session,
        source,
        entity_id=uuid.uuid4(),
        title="Test Fixture Notice Alpha",
        last_verified_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    index_document(
        db_session,
        source,
        entity_id=uuid.uuid4(),
        title="Test Fixture Notice Beta",
        last_verified_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC),
    )

    result = search_documents(
        db_session, q="fixture", locale="en", sort=SearchSortOption.LAST_VERIFIED
    )

    assert result.rows[0].document.title == "Test Fixture Notice Beta"


def test_similarity_threshold_constant_is_stricter_than_zero() -> None:
    # A sanity check on the documented constant itself (docs/SEARCH.md §5)
    # rather than a database round trip.
    assert 0 < TRIGRAM_SIMILARITY_THRESHOLD < 1
