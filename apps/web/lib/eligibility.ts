import type {
  EligibilityAnswers,
  EligibilityCriteriaResponse,
  EligibilityEntityType,
  EligibilityEvaluateResponse,
} from "@civiclens/types";
import {
  eligibilityCriteriaResponseSchema,
  eligibilityEvaluateResponseSchema,
} from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type EligibilityCriteriaApiResult =
  | { reachable: true; data: EligibilityCriteriaResponse }
  | { reachable: false; error: string }
  | { reachable: true; data: null };

export type EligibilityEvaluateApiResult =
  { reachable: true; data: EligibilityEvaluateResponse } | { reachable: false; error: string };

/**
 * Calls `GET /api/v1/eligibility/criteria` (docs/API.md §18). A 404 is
 * not an error state — it means "no such entity" (or, indistinguishably
 * to the public, "not yet published") and is reported as
 * `{ reachable: true; data: null }`, mirroring `getDocumentBySlug`'s
 * identical convention.
 */
export async function getEligibilityCriteria(
  entityType: EligibilityEntityType,
  entitySlug: string,
): Promise<EligibilityCriteriaApiResult> {
  try {
    const query = new URLSearchParams({ entity_type: entityType, entity_slug: entitySlug });
    const response = await fetch(
      `${API_BASE_URL}/api/v1/eligibility/criteria?${query.toString()}`,
      {
        cache: "no-store",
        signal: AbortSignal.timeout(5000),
      },
    );

    if (response.status === 404) {
      return { reachable: true, data: null };
    }
    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = eligibilityCriteriaResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

/**
 * Calls `POST /api/v1/eligibility/evaluate`. Runs client-side (called
 * from `EligibilityForm`, a "use client" component) since it submits a
 * citizen's own answers interactively — never persisted anywhere on this
 * side either (docs/PRIVACY.md, this phase's §G).
 */
export async function evaluateEligibility(
  entityType: EligibilityEntityType,
  entitySlug: string,
  answers: EligibilityAnswers,
): Promise<EligibilityEvaluateApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/eligibility/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entity_type: entityType, entity_slug: entitySlug, answers }),
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = eligibilityEvaluateResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}
