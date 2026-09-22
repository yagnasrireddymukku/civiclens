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

/**
 * Mirrors `apps/api/app/services/schemas.py` and
 * `apps/api/app/services/enums.py` exactly (Phase 7, the second real
 * domain module). `OrganizationSummary`/`DepartmentSummary`/
 * `SourceSummary`/`PaginationMeta` above are reused as-is.
 */
export type ServiceCategory =
  | "CERTIFICATES"
  | "DOCUMENTS"
  | "WELFARE"
  | "EDUCATION"
  | "HEALTHCARE"
  | "AGRICULTURE"
  | "EMPLOYMENT"
  | "BUSINESS"
  | "TRANSPORT"
  | "MUNICIPAL"
  | "REVENUE"
  | "SOCIAL_SECURITY"
  | "IDENTITY"
  | "UTILITIES"
  | "OTHER";

export type DeliveryMode = "ONLINE" | "OFFLINE" | "BOTH";

export type RequirementType = "AGE" | "RESIDENCY" | "INCOME" | "OCCUPATION" | "OTHER";

export type ApplicationChannelType =
  | "ONLINE"
  | "OFFLINE"
  | "MOBILE_APP"
  | "MEESEVA"
  | "DEPARTMENT_PORTAL"
  | "SERVICE_CENTER"
  | "IN_PERSON"
  | "OTHER";

export interface ServiceListItem {
  slug: string;
  name: string;
  organization: OrganizationSummary;
  department: DepartmentSummary | null;
  short_description: string | null;
  category: ServiceCategory;
  service_type: string | null;
  delivery_mode: DeliveryMode;
  state: string | null;
  district: string | null;
  status: string | null;
  verification_status: VerificationStatus;
  last_verified: string | null;
  source: SourceSummary;
}

export interface RequirementSummary {
  requirement_type: RequirementType;
  description: string;
  min_value: number | null;
  max_value: number | null;
}

export interface RequiredDocumentSummary {
  name: string;
  description: string | null;
  is_mandatory: boolean;
}

export interface ApplicationMethodSummary {
  channel_type: ApplicationChannelType;
  url: string | null;
  instructions: string | null;
}

export interface ServiceDetail {
  slug: string;
  name: string;
  organization: OrganizationSummary;
  department: DepartmentSummary | null;
  short_description: string | null;
  description: string | null;
  category: ServiceCategory;
  service_type: string | null;
  target_audience: string | null;
  delivery_mode: DeliveryMode;
  state: string | null;
  district: string | null;
  official_service_url: string | null;
  application_url: string | null;
  fee_summary: string | null;
  processing_time_summary: string | null;
  location_summary: string | null;
  status: string | null;
  verification_status: VerificationStatus;
  last_verified: string | null;
  source: SourceSummary;
  requirements: RequirementSummary[];
  required_documents: RequiredDocumentSummary[];
  application_methods: ApplicationMethodSummary[];
}

export interface ServiceListResponse {
  results: ServiceListItem[];
  pagination: PaginationMeta;
}

/**
 * Mirrors `apps/api/app/schemes/schemas.py` and
 * `apps/api/app/schemes/enums.py` exactly (Phase 8, the third real
 * domain module). `OrganizationSummary`/`DepartmentSummary`/
 * `SourceSummary`/`PaginationMeta` above are reused as-is, as are
 * `RequirementType`/`ApplicationChannelType`/`RequirementSummary`/
 * `RequiredDocumentSummary`/`ApplicationMethodSummary` — the shared
 * vocabulary Services already established, now confirmed by a second
 * consumer (backend `app.requirements.enums`).
 */
export type SchemeCategory =
  | "SCHOLARSHIP"
  | "PENSION"
  | "SUBSIDY"
  | "FINANCIAL_ASSISTANCE"
  | "INSURANCE"
  | "HOUSING"
  | "HEALTHCARE"
  | "EDUCATION"
  | "AGRICULTURE"
  | "EMPLOYMENT"
  | "SKILL_DEVELOPMENT"
  | "WOMEN_CHILD_WELFARE"
  | "SOCIAL_WELFARE"
  | "BUSINESS_ENTREPRENEURSHIP"
  | "DISABILITY_SUPPORT"
  | "OTHER";

export type BenefitType =
  | "CASH_TRANSFER"
  | "SUBSIDY"
  | "SCHOLARSHIP_AMOUNT"
  | "PENSION"
  | "INSURANCE_COVERAGE"
  | "LOAN_SUBSIDY"
  | "IN_KIND_SUPPORT"
  | "OTHER";

export interface SchemeListItem {
  slug: string;
  name: string;
  organization: OrganizationSummary;
  department: DepartmentSummary | null;
  short_description: string | null;
  category: SchemeCategory;
  state: string | null;
  district: string | null;
  status: string | null;
  verification_status: VerificationStatus;
  last_verified: string | null;
  source: SourceSummary;
}

export interface BenefitSummary {
  benefit_type: BenefitType;
  description: string;
  amount_summary: string | null;
  frequency_summary: string | null;
}

export interface RelatedServiceSummary {
  slug: string;
  name: string;
  note: string | null;
}

/**
 * Mirrors `apps/api/app/schemes/schemas.py::ScholarshipDetailSummary`
 * exactly (Phase 9, docs/DATABASE.md §13). Present only on
 * `SchemeDetail.scholarship` when the scheme has a backend
 * `ScholarshipDetail` row (i.e. is a `category: "SCHOLARSHIP"` scheme) —
 * `null` for every other category, not an object of all-`null` fields.
 * `minimum_percentage`/`minimum_cgpa` are `string`, not `number` —
 * verified directly against a real `TestClient` response (not assumed):
 * Pydantic v2 serializes a `Decimal` response-model field as a JSON
 * string ("60.00"), preserving exact precision rather than risking
 * float rounding on the wire. The live smoke test caught an earlier,
 * wrong assumption here that `jsonable_encoder` alone (called outside
 * a real response-model serialization path) had suggested a plain
 * number.
 */
export type EducationLevel =
  | "SCHOOL"
  | "INTERMEDIATE"
  | "DIPLOMA"
  | "UNDERGRADUATE"
  | "POSTGRADUATE"
  | "DOCTORAL"
  | "PROFESSIONAL"
  | "VOCATIONAL"
  | "OTHER";

export type StudyMode = "FULL_TIME" | "PART_TIME" | "DISTANCE" | "ONLINE" | "OTHER";

export interface ScholarshipDetailSummary {
  education_level: EducationLevel | null;
  course_discipline: string | null;
  institution_type: string | null;
  study_mode: StudyMode | null;
  year_of_study: string | null;
  minimum_percentage: string | null;
  minimum_cgpa: string | null;
  academic_requirement_notes: string | null;
  application_opens: string | null;
  application_closes: string | null;
  correction_window_end: string | null;
  academic_year: string | null;
  renewable: boolean;
  renewal_notes: string | null;
}

export interface SchemeDetail {
  slug: string;
  name: string;
  organization: OrganizationSummary;
  department: DepartmentSummary | null;
  short_description: string | null;
  description: string | null;
  category: SchemeCategory;
  target_audience: string | null;
  state: string | null;
  district: string | null;
  official_scheme_url: string | null;
  application_url: string | null;
  status: string | null;
  verification_status: VerificationStatus;
  last_verified: string | null;
  source: SourceSummary;
  benefits: BenefitSummary[];
  requirements: RequirementSummary[];
  required_documents: RequiredDocumentSummary[];
  application_methods: ApplicationMethodSummary[];
  related_services: RelatedServiceSummary[];
  scholarship: ScholarshipDetailSummary | null;
}

export interface SchemeListResponse {
  results: SchemeListItem[];
  pagination: PaginationMeta;
}

/**
 * Mirrors `apps/api/app/documents/schemas.py` and
 * `apps/api/app/documents/enums.py` exactly (Phase 10, the fourth real
 * domain module). `OrganizationSummary`/`DepartmentSummary`/
 * `SourceSummary`/`PaginationMeta`/`RequirementType`/
 * `ApplicationChannelType`/`DeliveryMode`/`RequirementSummary`/
 * `ApplicationMethodSummary` above are reused as-is — the shared
 * vocabulary Services/Schemes already established, now confirmed by a
 * fourth consumer.
 */
export type DocumentType =
  "CERTIFICATE" | "IDENTITY_DOCUMENT" | "RECORD" | "PERMIT" | "LICENSE" | "REGISTRATION" | "OTHER";

export type DocumentCategory =
  | "PERSONAL"
  | "IDENTITY"
  | "RESIDENCE"
  | "INCOME"
  | "SOCIAL_CATEGORY"
  | "EDUCATION"
  | "BIRTH_DEATH"
  | "DISABILITY"
  | "LAND_REVENUE"
  | "EMPLOYMENT"
  | "BUSINESS"
  | "FAMILY"
  | "OTHER";

export interface DocumentListItem {
  slug: string;
  name: string;
  organization: OrganizationSummary;
  department: DepartmentSummary | null;
  short_description: string | null;
  document_type: DocumentType;
  category: DocumentCategory;
  delivery_mode: DeliveryMode;
  state: string | null;
  district: string | null;
  status: string | null;
  verification_status: VerificationStatus;
  last_verified: string | null;
  source: SourceSummary;
}

export interface CivicDocumentRefSummary {
  slug: string;
  name: string;
}

export interface SupportingDocumentSummary {
  name: string;
  description: string | null;
  is_mandatory: boolean;
  // Present only when this supporting document is itself a modeled
  // `CivicDocument` (this phase's §11) — `null` when it's free text
  // only.
  civic_document: CivicDocumentRefSummary | null;
}

export interface ServiceRefSummary {
  slug: string;
  name: string;
}

export interface RequiredBySummary {
  entity_type: "service" | "scheme";
  slug: string;
  name: string;
}

export interface DocumentDetail {
  slug: string;
  name: string;
  organization: OrganizationSummary;
  department: DepartmentSummary | null;
  short_description: string | null;
  description: string | null;
  document_type: DocumentType;
  category: DocumentCategory;
  purpose: string | null;
  delivery_mode: DeliveryMode;
  state: string | null;
  district: string | null;
  official_document_url: string | null;
  application_url: string | null;
  fee_summary: string | null;
  processing_time_summary: string | null;
  validity_summary: string | null;
  renewal_summary: string | null;
  status: string | null;
  verification_status: VerificationStatus;
  last_verified: string | null;
  source: SourceSummary;
  requirements: RequirementSummary[];
  supporting_documents: SupportingDocumentSummary[];
  application_methods: ApplicationMethodSummary[];
  // The "obtained through" relationship (this phase's §13) — `null`
  // when no modeled `Service` exists, or it isn't itself publicly
  // visible.
  service: ServiceRefSummary | null;
  // "Where this document may be required" (this phase's §21/§22).
  required_by: RequiredBySummary[];
}

export interface DocumentListResponse {
  results: DocumentListItem[];
  pagination: PaginationMeta;
}
