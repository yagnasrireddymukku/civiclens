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
