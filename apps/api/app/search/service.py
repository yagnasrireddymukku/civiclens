"""The search abstraction (this phase's §4): the only code path that
writes to or queries `search_documents`. Future domain modules call
`upsert_search_document`/`remove_search_document` when they publish or
retire an entity; nothing outside this module constructs a `tsquery` or
touches `search_vector` directly. Replacing the underlying engine later
(docs/SEARCH.md §10) means rewriting this module, not every caller.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypedDict

from sqlalchemy import ColumnElement, Select, delete, func, literal_column, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.geography.models import District, State
from app.search.enums import SearchSortOption
from app.search.models import SearchDocument
from app.sources.enums import VerificationStatus
from app.sources.models import Source

# Uses word_similarity(), not similarity() — verified by hand this
# distinction matters: plain similarity() scores the *entire* title
# against the query, so a short query ("pasport") against a long title
# ("Test Passport Renewal Notice (Fixture)") gets diluted to ~0.18 even
# though it's an obvious one-letter typo of a word actually in the
# title. word_similarity() instead scores the query against its
# best-matching substring of the title, giving "pasport" -> 0.70 against
# that same title. Threshold tuned against fictional fixtures measured
# directly: "pasport" (a real typo) -> 0.70, unrelated text -> 0.0;
# 0.4 sits well clear of both. Documented per docs/SEARCH.md §5.
TRIGRAM_SIMILARITY_THRESHOLD = 0.4

_ENGLISH_CONFIG = "english"
# PostgreSQL has no Telugu text-search configuration (no stemming
# dictionary) — "simple" (unstemmed) is the honest, documented MVP
# choice, per docs/SEARCH.md §7. This is a known limitation, not a
# silent gap: Telugu ranking quality is expected to lag English.
_TELUGU_FALLBACK_CONFIG = "simple"


def _ts_config(locale: str) -> str:
    return _ENGLISH_CONFIG if locale == "en" else _TELUGU_FALLBACK_CONFIG


def _build_search_vector_expr(
    config: str, title: str, summary: str | None, searchable_text: str | None
) -> ColumnElement[Any]:
    """Weighted per docs/SEARCH.md §3: title (A) outranks summary (B)
    outranks incidental body text (C).

    The weight labels are inlined via `literal_column` rather than bound
    as ordinary parameters — verified necessary by hand: `setweight`'s
    second argument is Postgres's internal one-byte `"char"` type, not
    `varchar`/`text`. A normal SQLAlchemy string parameter is sent with
    an explicit `::VARCHAR` cast, which fails with "function setweight
    (tsvector, character varying) does not exist" since there's no
    implicit cast from `varchar` to `"char"`. An inlined, unquoted-type
    literal lets Postgres apply its usual untyped-string-literal
    inference instead, which does resolve to `"char"` here. The literal
    is one of a fixed, hardcoded set ('A'/'B'/'C') — never
    caller-supplied input — so this is not a SQL-injection risk.
    """
    title_vector = func.setweight(func.to_tsvector(config, title), literal_column("'A'"))
    summary_vector = func.setweight(func.to_tsvector(config, summary or ""), literal_column("'B'"))
    body_vector = func.setweight(
        func.to_tsvector(config, searchable_text or ""), literal_column("'C'")
    )
    return title_vector.op("||")(summary_vector).op("||")(body_vector)


_INDEXABLE_STATUSES = (VerificationStatus.VERIFIED, VerificationStatus.NEEDS_REVIEW)


class _FilterKwargs(TypedDict):
    """Keyword shape shared by every `_apply_filters` call site in
    `search_documents` — a plain `dict(...)` can't be checked against
    `_apply_filters`'s individually-typed keyword-only parameters when
    unpacked with `**`, so this gives mypy something concrete to match."""

    locale: str
    entity_type: str | None
    state_id: uuid.UUID | None
    district_id: uuid.UUID | None
    category: str | None
    status: str | None
    date_from: datetime | None
    date_to: datetime | None


def upsert_search_document(
    session: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    locale: str,
    title: str,
    source_id: uuid.UUID,
    verification_status: VerificationStatus,
    summary: str | None = None,
    searchable_text: str | None = None,
    route: str = "",
    state_id: uuid.UUID | None = None,
    district_id: uuid.UUID | None = None,
    category: str | None = None,
    status: str | None = None,
    last_verified_at: datetime | None = None,
) -> None:
    """The only write path onto `search_documents` — an insert-or-update
    keyed on (entity_type, entity_id, locale), matching docs/SEARCH.md
    §1's "indexing is one-directional, domain tables -> index."

    Refuses to index anything but VERIFIED/NEEDS_REVIEW
    (docs/SEARCH.md §3, docs/DATA_GOVERNANCE.md §4) — call
    `remove_search_document` when an entity becomes UNVERIFIED, EXPIRED,
    or is soft-deleted, rather than upserting it here with a different
    status.
    """
    if verification_status not in _INDEXABLE_STATUSES:
        raise ValueError(
            f"Refusing to index a document with verification_status="
            f"{verification_status!r} — only {_INDEXABLE_STATUSES} are indexed "
            "(docs/SEARCH.md §3). Call remove_search_document instead."
        )

    config = _ts_config(locale)
    search_vector_expr = _build_search_vector_expr(config, title, summary, searchable_text)

    values: dict[str, object] = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "locale": locale,
        "title": title,
        "summary": summary,
        "searchable_text": searchable_text,
        "route": route,
        "state_id": state_id,
        "district_id": district_id,
        "category": category,
        "status": status,
        "source_id": source_id,
        "verification_status": verification_status,
        "last_verified_at": last_verified_at,
        "search_vector": search_vector_expr,
    }

    stmt = pg_insert(SearchDocument).values(**values)
    update_columns: dict[str, ColumnElement[Any]] = {
        key: stmt.excluded[key]
        for key in values
        if key not in ("entity_type", "entity_id", "locale")
    }
    update_columns["updated_at"] = func.now()
    stmt = stmt.on_conflict_do_update(
        constraint="uq_search_documents_entity_locale",
        set_=update_columns,
    )
    session.execute(stmt)


def remove_search_document(
    session: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    locale: str | None = None,
) -> None:
    """Removes a document from the index — for an entity that becomes
    UNVERIFIED/EXPIRED/soft-deleted, or no longer exists. `locale=None`
    removes every locale's document for that entity."""
    stmt = delete(SearchDocument).where(
        SearchDocument.entity_type == entity_type,
        SearchDocument.entity_id == entity_id,
    )
    if locale is not None:
        stmt = stmt.where(SearchDocument.locale == locale)
    session.execute(stmt)


def _apply_filters(
    stmt: Select[Any],
    *,
    locale: str,
    entity_type: str | None,
    state_id: uuid.UUID | None,
    district_id: uuid.UUID | None,
    category: str | None,
    status: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select[Any]:
    """Applied identically to the count query and the results query, and
    to both the exact and fuzzy match branches — filters are always AND
    conditions alongside the text predicate (docs/API.md §6,
    docs/SEARCH.md §6), never post-filtering an already-paged result."""
    stmt = stmt.where(SearchDocument.locale == locale)
    if entity_type is not None:
        stmt = stmt.where(SearchDocument.entity_type == entity_type)
    if state_id is not None:
        stmt = stmt.where(SearchDocument.state_id == state_id)
    if district_id is not None:
        stmt = stmt.where(SearchDocument.district_id == district_id)
    if category is not None:
        stmt = stmt.where(SearchDocument.category == category)
    if status is not None:
        stmt = stmt.where(SearchDocument.status == status)
    if date_from is not None:
        stmt = stmt.where(SearchDocument.last_verified_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(SearchDocument.last_verified_at <= date_to)
    return stmt


def _order_by_relevance_or_recency(
    stmt: Select[Any], relevance_score: ColumnElement[Any], sort: SearchSortOption
) -> Select[Any]:
    """`sort=last_verified` always wins; otherwise order by the given
    relevance score (rank or trigram similarity, whichever branch is
    active) with recency as the tie-breaker — never popularity or any
    other engagement signal (this phase's §10, docs/SEARCH.md §8)."""
    recency = SearchDocument.last_verified_at.desc().nullslast()
    if sort == SearchSortOption.LAST_VERIFIED:
        return stmt.order_by(recency)
    return stmt.order_by(relevance_score.desc(), recency)


@dataclass
class SearchResultRow:
    document: SearchDocument
    state_name: str | None
    district_name: str | None
    source: Source


@dataclass
class SearchQueryResult:
    rows: list[SearchResultRow]
    total_count: int
    fuzzy_fallback_used: bool


def _count(stmt_filters: Select[Any]) -> Select[Any]:
    return select(func.count()).select_from(stmt_filters.subquery())


def search_documents(
    session: Session,
    *,
    q: str,
    locale: str = "en",
    entity_type: str | None = None,
    state_id: uuid.UUID | None = None,
    district_id: uuid.UUID | None = None,
    category: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: SearchSortOption = SearchSortOption.RELEVANCE,
) -> SearchQueryResult:
    """The query engine half of the abstraction. Query flow
    (docs/SEARCH.md §5, §8):

    1. If `q` is blank, this is a filters-only browse — order by recency.
    2. Otherwise, try an exact/`tsquery` full-text match first.
    3. If that returns zero rows, fall back to `pg_trgm` similarity on
       the title for typo tolerance — never run both and merge scores,
       which would make ranking non-deterministic and hard to test.
    """
    config = _ts_config(locale)
    query_text = q.strip()

    def base_row_select() -> Select[Any]:
        return (
            select(SearchDocument, State.name, District.name, Source)
            .outerjoin(State, SearchDocument.state_id == State.id)
            .outerjoin(District, SearchDocument.district_id == District.id)
            .join(Source, SearchDocument.source_id == Source.id)
        )

    def base_count_select() -> Select[Any]:
        return select(SearchDocument.id)

    common_filter_kwargs: _FilterKwargs = dict(
        locale=locale,
        entity_type=entity_type,
        state_id=state_id,
        district_id=district_id,
        category=category,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    fuzzy_fallback_used = False

    if not query_text:
        row_stmt = _apply_filters(base_row_select(), **common_filter_kwargs)
        row_stmt = row_stmt.order_by(SearchDocument.last_verified_at.desc().nullslast())
        total_count = session.scalar(
            _count(_apply_filters(base_count_select(), **common_filter_kwargs))
        )
    else:
        tsquery = func.websearch_to_tsquery(config, query_text)
        exact_predicate = SearchDocument.search_vector.op("@@")(tsquery)

        exact_count_stmt = _apply_filters(base_count_select(), **common_filter_kwargs).where(
            exact_predicate
        )
        exact_total = session.scalar(_count(exact_count_stmt)) or 0

        if exact_total > 0:
            rank = func.ts_rank_cd(SearchDocument.search_vector, tsquery)
            row_stmt = _apply_filters(base_row_select(), **common_filter_kwargs).where(
                exact_predicate
            )
            row_stmt = _order_by_relevance_or_recency(row_stmt, rank, sort)
            total_count = exact_total
        else:
            fuzzy_fallback_used = True
            similarity = func.word_similarity(query_text, SearchDocument.title)
            fuzzy_predicate = similarity > TRIGRAM_SIMILARITY_THRESHOLD

            row_stmt = _apply_filters(base_row_select(), **common_filter_kwargs).where(
                fuzzy_predicate
            )
            row_stmt = _order_by_relevance_or_recency(row_stmt, similarity, sort)
            total_count = session.scalar(
                _count(
                    _apply_filters(base_count_select(), **common_filter_kwargs).where(
                        fuzzy_predicate
                    )
                )
            )

    total_count = total_count or 0

    paged_stmt = row_stmt.offset((page - 1) * page_size).limit(page_size)
    rows = [
        SearchResultRow(
            document=document, state_name=state_name, district_name=district_name, source=source
        )
        for document, state_name, district_name, source in session.execute(paged_stmt).all()
    ]

    return SearchQueryResult(
        rows=rows, total_count=total_count, fuzzy_fallback_used=fuzzy_fallback_used
    )
