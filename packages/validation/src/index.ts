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
