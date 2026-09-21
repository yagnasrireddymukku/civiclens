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
