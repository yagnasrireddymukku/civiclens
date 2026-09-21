"""Request/response contract for GET /api/v1/search — see docs/API.md
§5-9 for the conventions every field here follows (Pydantic validation,
explicit enums, provenance-carrying response shape, standard pagination).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.search.enums import SearchSortOption
from app.sources.enums import VerificationStatus

MAX_QUERY_LENGTH = 200
MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20


class SearchQueryParams(BaseModel):
    """Validated query parameters. FastAPI's `Query(...)` dependency
    injection binds request query params to these fields; nothing in the
    route handler reads raw/untyped query data (docs/API.md §5)."""

    model_config = ConfigDict(extra="forbid")

    q: str = Field(default="", max_length=MAX_QUERY_LENGTH)
    entity_type: str | None = Field(default=None, max_length=50)
    state_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    category: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=50)
    date_from: datetime | None = None
    date_to: datetime | None = None
    locale: str = Field(default="en", max_length=10)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    sort: SearchSortOption = SearchSortOption.RELEVANCE


class SourceSummary(BaseModel):
    """Provenance must survive into search results — this phase's §13,
    docs/DATA_GOVERNANCE.md §3. Never omitted from a result."""

    organization: str
    title: str
    url: str


class SearchResultItem(BaseModel):
    # A stable, public composite identifier — never the raw internal
    # `search_documents.id` (docs/API.md §12's "don't expose internal
    # database IDs unnecessarily" convention).
    id: str
    entity_type: str
    title: str
    summary: str | None
    route: str
    state: str | None
    district: str | None
    category: str | None
    status: str | None
    verification_status: VerificationStatus
    source: SourceSummary
    last_verified: datetime | None


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int


class QueryMeta(BaseModel):
    q: str
    locale: str
    fuzzy_fallback_used: bool


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    pagination: PaginationMeta
    query: QueryMeta
