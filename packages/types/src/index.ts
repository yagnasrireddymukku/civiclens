/**
 * Shared TypeScript types consumed by apps/web (and, later, other
 * frontends). From Phase 2 onward, domain types are generated from the
 * FastAPI OpenAPI schema (docs/API.md §10) — hand-written types here should
 * shrink to zero as generation comes online. `HealthStatus` is a
 * placeholder proving the workspace-package wiring for Phase 1; it mirrors
 * the shape returned by `GET /api/v1/health` (apps/api).
 */
export interface HealthStatus {
  status: "ok";
  service: string;
  version: string;
  timestamp: string;
}

/**
 * Mirrors `apps/api/app/search/schemas.py` and
 * `apps/api/app/sources/enums.py::VerificationStatus` exactly — the first
 * hand-written domain type here (Phase 5), added ahead of OpenAPI
 * generation landing per the file-level note above.
 */
export type VerificationStatus = "VERIFIED" | "NEEDS_REVIEW" | "EXPIRED" | "UNVERIFIED";

export type SearchSortOption = "relevance" | "last_verified";

export interface SourceSummary {
  organization: string;
  title: string;
  url: string;
}

export interface SearchResultItem {
  id: string;
  entity_type: string;
  title: string;
  summary: string | null;
  route: string;
  state: string | null;
  district: string | null;
  category: string | null;
  status: string | null;
  verification_status: VerificationStatus;
  source: SourceSummary;
  last_verified: string | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_count: number;
}

export interface QueryMeta {
  q: string;
  locale: string;
  fuzzy_fallback_used: boolean;
}

export interface SearchResponse {
  results: SearchResultItem[];
  pagination: PaginationMeta;
  query: QueryMeta;
}
