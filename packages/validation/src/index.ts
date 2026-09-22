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

/**
 * Mirrors `apps/api/app/services/schemas.py` exactly (Phase 7). Reuses
 * `sourceSummarySchema`/`organizationSummarySchema`/
 * `departmentSummarySchema`/`paginationMetaSchema` above.
 */
export const serviceCategorySchema = z.enum([
  "CERTIFICATES",
  "DOCUMENTS",
  "WELFARE",
  "EDUCATION",
  "HEALTHCARE",
  "AGRICULTURE",
  "EMPLOYMENT",
  "BUSINESS",
  "TRANSPORT",
  "MUNICIPAL",
  "REVENUE",
  "SOCIAL_SECURITY",
  "IDENTITY",
  "UTILITIES",
  "OTHER",
]);

export const deliveryModeSchema = z.enum(["ONLINE", "OFFLINE", "BOTH"]);

export const requirementTypeSchema = z.enum(["AGE", "RESIDENCY", "INCOME", "OCCUPATION", "OTHER"]);

export const applicationChannelTypeSchema = z.enum([
  "ONLINE",
  "OFFLINE",
  "MOBILE_APP",
  "MEESEVA",
  "DEPARTMENT_PORTAL",
  "SERVICE_CENTER",
  "IN_PERSON",
  "OTHER",
]);

export const serviceListItemSchema = z.object({
  slug: z.string(),
  name: z.string(),
  organization: organizationSummarySchema,
  department: departmentSummarySchema.nullable(),
  short_description: z.string().nullable(),
  category: serviceCategorySchema,
  service_type: z.string().nullable(),
  delivery_mode: deliveryModeSchema,
  state: z.string().nullable(),
  district: z.string().nullable(),
  status: z.string().nullable(),
  verification_status: verificationStatusSchema,
  last_verified: z.string().nullable(),
  source: sourceSummarySchema,
});

export const requirementSummarySchema = z.object({
  requirement_type: requirementTypeSchema,
  description: z.string(),
  min_value: z.number().nullable(),
  max_value: z.number().nullable(),
});

export const requiredDocumentSummarySchema = z.object({
  name: z.string(),
  description: z.string().nullable(),
  is_mandatory: z.boolean(),
});

export const applicationMethodSummarySchema = z.object({
  channel_type: applicationChannelTypeSchema,
  url: z.string().nullable(),
  instructions: z.string().nullable(),
});

export const serviceDetailSchema = z.object({
  slug: z.string(),
  name: z.string(),
  organization: organizationSummarySchema,
  department: departmentSummarySchema.nullable(),
  short_description: z.string().nullable(),
  description: z.string().nullable(),
  category: serviceCategorySchema,
  service_type: z.string().nullable(),
  target_audience: z.string().nullable(),
  delivery_mode: deliveryModeSchema,
  state: z.string().nullable(),
  district: z.string().nullable(),
  official_service_url: z.string().nullable(),
  application_url: z.string().nullable(),
  fee_summary: z.string().nullable(),
  processing_time_summary: z.string().nullable(),
  location_summary: z.string().nullable(),
  status: z.string().nullable(),
  verification_status: verificationStatusSchema,
  last_verified: z.string().nullable(),
  source: sourceSummarySchema,
  requirements: z.array(requirementSummarySchema),
  required_documents: z.array(requiredDocumentSummarySchema),
  application_methods: z.array(applicationMethodSummarySchema),
});

export const serviceListResponseSchema = z.object({
  results: z.array(serviceListItemSchema),
  pagination: paginationMetaSchema,
});

export type ServiceDetailInput = z.infer<typeof serviceDetailSchema>;
export type ServiceListResponseInput = z.infer<typeof serviceListResponseSchema>;

/**
 * Mirrors `apps/api/app/schemes/schemas.py` exactly (Phase 8). Reuses
 * `sourceSummarySchema`/`organizationSummarySchema`/
 * `departmentSummarySchema`/`paginationMetaSchema`/
 * `requirementTypeSchema`/`applicationChannelTypeSchema`/
 * `requirementSummarySchema`/`requiredDocumentSummarySchema`/
 * `applicationMethodSummarySchema` above.
 */
export const schemeCategorySchema = z.enum([
  "SCHOLARSHIP",
  "PENSION",
  "SUBSIDY",
  "FINANCIAL_ASSISTANCE",
  "INSURANCE",
  "HOUSING",
  "HEALTHCARE",
  "EDUCATION",
  "AGRICULTURE",
  "EMPLOYMENT",
  "SKILL_DEVELOPMENT",
  "WOMEN_CHILD_WELFARE",
  "SOCIAL_WELFARE",
  "BUSINESS_ENTREPRENEURSHIP",
  "DISABILITY_SUPPORT",
  "OTHER",
]);

export const benefitTypeSchema = z.enum([
  "CASH_TRANSFER",
  "SUBSIDY",
  "SCHOLARSHIP_AMOUNT",
  "PENSION",
  "INSURANCE_COVERAGE",
  "LOAN_SUBSIDY",
  "IN_KIND_SUPPORT",
  "OTHER",
]);

export const schemeListItemSchema = z.object({
  slug: z.string(),
  name: z.string(),
  organization: organizationSummarySchema,
  department: departmentSummarySchema.nullable(),
  short_description: z.string().nullable(),
  category: schemeCategorySchema,
  state: z.string().nullable(),
  district: z.string().nullable(),
  status: z.string().nullable(),
  verification_status: verificationStatusSchema,
  last_verified: z.string().nullable(),
  source: sourceSummarySchema,
});

export const benefitSummarySchema = z.object({
  benefit_type: benefitTypeSchema,
  description: z.string(),
  amount_summary: z.string().nullable(),
  frequency_summary: z.string().nullable(),
});

export const relatedServiceSummarySchema = z.object({
  slug: z.string(),
  name: z.string(),
  note: z.string().nullable(),
});

export const schemeDetailSchema = z.object({
  slug: z.string(),
  name: z.string(),
  organization: organizationSummarySchema,
  department: departmentSummarySchema.nullable(),
  short_description: z.string().nullable(),
  description: z.string().nullable(),
  category: schemeCategorySchema,
  target_audience: z.string().nullable(),
  state: z.string().nullable(),
  district: z.string().nullable(),
  official_scheme_url: z.string().nullable(),
  application_url: z.string().nullable(),
  status: z.string().nullable(),
  verification_status: verificationStatusSchema,
  last_verified: z.string().nullable(),
  source: sourceSummarySchema,
  benefits: z.array(benefitSummarySchema),
  requirements: z.array(requirementSummarySchema),
  required_documents: z.array(requiredDocumentSummarySchema),
  application_methods: z.array(applicationMethodSummarySchema),
  related_services: z.array(relatedServiceSummarySchema),
});

export const schemeListResponseSchema = z.object({
  results: z.array(schemeListItemSchema),
  pagination: paginationMetaSchema,
});

export type SchemeDetailInput = z.infer<typeof schemeDetailSchema>;
export type SchemeListResponseInput = z.infer<typeof schemeListResponseSchema>;
