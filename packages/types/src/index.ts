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

/**
 * Mirrors `apps/api/app/jobs/schemas.py` and `apps/api/app/jobs/enums.py`
 * exactly (Phase 6, the first real domain module). `SourceSummary` and
 * `PaginationMeta` above are reused as-is — unlike the backend's
 * per-module Python files, this package has no module-boundary reason
 * to redeclare them.
 */
export type EmploymentType = "PERMANENT" | "CONTRACT" | "TEMPORARY";

export type JobNotificationStatus =
  | "DRAFT"
  | "REVIEW"
  | "PUBLISHED"
  | "APPLICATION_OPEN"
  | "APPLICATION_CLOSED"
  | "EXAMINATION"
  | "RESULT"
  | "ARCHIVED";

export interface OrganizationSummary {
  name: string;
  org_type: string;
}

export interface DepartmentSummary {
  name: string;
}

export interface JobListItem {
  slug: string;
  title: string;
  organization: OrganizationSummary;
  department: DepartmentSummary | null;
  summary: string | null;
  employment_type: EmploymentType;
  category: string | null;
  state: string;
  district: string | null;
  status: string | null;
  verification_status: VerificationStatus;
  last_verified: string | null;
  source: SourceSummary;
}

export interface VacancySummary {
  post_name: string;
  vacancy_count: number | null;
  category: string | null;
  location: string | null;
}

export interface NotificationSummary {
  notification_number: string | null;
  status: JobNotificationStatus;
  published_date: string | null;
  application_start: string | null;
  application_end: string | null;
  correction_window_end: string | null;
  exam_date: string | null;
  total_vacancies: number | null;
  official_notification_url: string | null;
  official_application_url: string | null;
  verification_status: VerificationStatus;
  last_verified: string | null;
  source: SourceSummary;
  vacancies: VacancySummary[];
}

export interface JobDetail {
  slug: string;
  title: string;
  organization: OrganizationSummary;
  department: DepartmentSummary | null;
  summary: string | null;
  description: string | null;
  employment_type: EmploymentType;
  category: string | null;
  state: string;
  district: string | null;
  min_age: number | null;
  max_age: number | null;
  qualification_summary: string | null;
  experience_summary: string | null;
  salary_summary: string | null;
  status: string | null;
  verification_status: VerificationStatus;
  last_verified: string | null;
  source: SourceSummary;
  notifications: NotificationSummary[];
}

export interface JobListResponse {
  results: JobListItem[];
  pagination: PaginationMeta;
}
