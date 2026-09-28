import type {
  AIAskResponse,
  AIEntityContext,
  AIExplainEligibilityResponse,
  EligibilityAnswers,
  EligibilityEntityType,
} from "@civiclens/types";
import { aiAskResponseSchema, aiExplainEligibilityResponseSchema } from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type AskCivicAIResult =
  { reachable: true; data: AIAskResponse } | { reachable: false; error: string };

export type ExplainEligibilityAIResult =
  { reachable: true; data: AIExplainEligibilityResponse } | { reachable: false; error: string };

/**
 * Calls `POST /api/v1/ai/ask` (docs/API.md §19). Runs client-side —
 * called from a "use client" form component, since it submits a
 * citizen's own question interactively and is never persisted anywhere
 * on this side either (docs/AI_ARCHITECTURE.md §7, this phase's §G).
 */
export async function askCivicAI(
  question: string,
  locale: string,
  entityContext?: AIEntityContext,
): Promise<AskCivicAIResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/ai/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, locale, entity_context: entityContext ?? null }),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = aiAskResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

/**
 * Calls `POST /api/v1/ai/explain-eligibility` — explains an already-
 * computed deterministic Eligibility Engine result in plain language;
 * never recomputes it (docs/AI_ARCHITECTURE.md, app/ai/eligibility_explainer.py).
 */
export async function explainEligibilityWithAI(
  entityType: EligibilityEntityType,
  entitySlug: string,
  answers: EligibilityAnswers,
  locale: string,
): Promise<ExplainEligibilityAIResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/ai/explain-eligibility`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entity_type: entityType, entity_slug: entitySlug, answers, locale }),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = aiExplainEligibilityResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}
