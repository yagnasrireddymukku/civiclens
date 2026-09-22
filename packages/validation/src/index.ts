import { z } from "zod";

/**
 * Placeholder schema proving the shared-validation package wiring for
 * Phase 1. It mirrors `@civiclens/types`' `HealthStatus`. Real domain
 * validation schemas (jobs, schemes, eligibility conditions, etc.) are
 * added per ROADMAP.md phase as each domain lands — nothing else belongs
 * here yet.
 */
export const healthStatusSchema = z.object({
  status: z.literal("ok"),
  service: z.string(),
  version: z.string(),
  timestamp: z.string(),
});

export type HealthStatusInput = z.infer<typeof healthStatusSchema>;

/**
 * Mirrors `apps/api/app/search/schemas.py::SearchResponse` and
 * `apps/api/app/sources/enums.py::VerificationStatus` exactly (Phase 5)
 * — see the file-level note above on this being hand-written ahead of
 * OpenAPI generation.
 */
export const verificationStatusSchema = z.enum([
  "VERIFIED",
  "NEEDS_REVIEW",
  "EXPIRED",
  "UNVERIFIED",
]);

export const sourceSummarySchema = z.object({
  organization: z.string(),
  title: z.string(),
  url: z.string(),
});

export const searchResultItemSchema = z.object({
  id: z.string(),
  entity_type: z.string(),
  title: z.string(),
  summary: z.string().nullable(),
  route: z.string(),
  state: z.string().nullable(),
  district: z.string().nullable(),
  category: z.string().nullable(),
  status: z.string().nullable(),
  verification_status: verificationStatusSchema,
  source: sourceSummarySchema,
  last_verified: z.string().nullable(),
});

export const paginationMetaSchema = z.object({
  page: z.number(),
  page_size: z.number(),
  total_count: z.number(),
});

export const queryMetaSchema = z.object({
  q: z.string(),
  locale: z.string(),
  fuzzy_fallback_used: z.boolean(),
});

export const searchResponseSchema = z.object({
  results: z.array(searchResultItemSchema),
  pagination: paginationMetaSchema,
  query: queryMetaSchema,
});

export type SearchResponseInput = z.infer<typeof searchResponseSchema>;

/**
 * Mirrors `apps/api/app/jobs/schemas.py` exactly (Phase 6). Reuses
 * `sourceSummarySchema`/`paginationMetaSchema` above rather than
 * redeclaring them — no module-boundary reason to duplicate within this
 * single shared package.
 */
export const employmentTypeSchema = z.enum(["PERMANENT", "CONTRACT", "TEMPORARY"]);

export const jobNotificationStatusSchema = z.enum([
  "DRAFT",
  "REVIEW",
  "PUBLISHED",
  "APPLICATION_OPEN",
  "APPLICATION_CLOSED",
  "EXAMINATION",
  "RESULT",
  "ARCHIVED",
]);

export const organizationSummarySchema = z.object({
  name: z.string(),
  org_type: z.string(),
});

export const departmentSummarySchema = z.object({
  name: z.string(),
});

export const jobListItemSchema = z.object({
  slug: z.string(),
  title: z.string(),
  organization: organizationSummarySchema,
  department: departmentSummarySchema.nullable(),
  summary: z.string().nullable(),
  employment_type: employmentTypeSchema,
  category: z.string().nullable(),
  state: z.string(),
  district: z.string().nullable(),
  status: z.string().nullable(),
  verification_status: verificationStatusSchema,
  last_verified: z.string().nullable(),
  source: sourceSummarySchema,
});

export const vacancySummarySchema = z.object({
  post_name: z.string(),
  vacancy_count: z.number().nullable(),
  category: z.string().nullable(),
  location: z.string().nullable(),
});

export const notificationSummarySchema = z.object({
  notification_number: z.string().nullable(),
  status: jobNotificationStatusSchema,
  published_date: z.string().nullable(),
  application_start: z.string().nullable(),
  application_end: z.string().nullable(),
  correction_window_end: z.string().nullable(),
  exam_date: z.string().nullable(),
  total_vacancies: z.number().nullable(),
  official_notification_url: z.string().nullable(),
  official_application_url: z.string().nullable(),
  verification_status: verificationStatusSchema,
  last_verified: z.string().nullable(),
  source: sourceSummarySchema,
  vacancies: z.array(vacancySummarySchema),
});

export const jobDetailSchema = z.object({
  slug: z.string(),
  title: z.string(),
  organization: organizationSummarySchema,
  department: departmentSummarySchema.nullable(),
  summary: z.string().nullable(),
  description: z.string().nullable(),
  employment_type: employmentTypeSchema,
  category: z.string().nullable(),
  state: z.string(),
  district: z.string().nullable(),
  min_age: z.number().nullable(),
  max_age: z.number().nullable(),
  qualification_summary: z.string().nullable(),
  experience_summary: z.string().nullable(),
  salary_summary: z.string().nullable(),
  status: z.string().nullable(),
  verification_status: verificationStatusSchema,
  last_verified: z.string().nullable(),
  source: sourceSummarySchema,
  notifications: z.array(notificationSummarySchema),
});

export const jobListResponseSchema = z.object({
  results: z.array(jobListItemSchema),
  pagination: paginationMetaSchema,
});

export type JobDetailInput = z.infer<typeof jobDetailSchema>;
export type JobListResponseInput = z.infer<typeof jobListResponseSchema>;
