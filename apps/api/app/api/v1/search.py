"""GET /api/v1/search — see docs/API.md §6 for the pagination/filtering/
sorting conventions this follows, and docs/SEARCH.md for the underlying
query flow. Route handlers here only translate between HTTP and
`app.search.service` — no query-building logic lives in this file.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.search import service
from app.search.schemas import (
    PaginationMeta,
    QueryMeta,
    SearchQueryParams,
    SearchResponse,
    SearchResultItem,
    SourceSummary,
)

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
def get_search_results(
    params: Annotated[SearchQueryParams, Query()],
    db: Session = Depends(get_db),
) -> SearchResponse:
    result = service.search_documents(
        db,
        q=params.q,
        locale=params.locale,
        entity_type=params.entity_type,
        state_id=params.state_id,
        district_id=params.district_id,
        category=params.category,
        status=params.status,
        date_from=params.date_from,
        date_to=params.date_to,
        page=params.page,
        page_size=params.page_size,
        sort=params.sort,
    )

    results = [
        SearchResultItem(
            id=f"{row.document.entity_type}:{row.document.entity_id}",
            entity_type=row.document.entity_type,
            title=row.document.title,
            summary=row.document.summary,
            route=row.document.route,
            state=row.state_name,
            district=row.district_name,
            category=row.document.category,
            status=row.document.status,
            verification_status=row.document.verification_status,
            source=SourceSummary(
                organization=row.source.organization,
                title=row.source.title,
                url=row.source.url,
            ),
            last_verified=row.document.last_verified_at,
        )
        for row in result.rows
    ]

    return SearchResponse(
        results=results,
        pagination=PaginationMeta(
            page=params.page, page_size=params.page_size, total_count=result.total_count
        ),
        query=QueryMeta(
            q=params.q, locale=params.locale, fuzzy_fallback_used=result.fuzzy_fallback_used
        ),
    )
