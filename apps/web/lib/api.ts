import type { HealthStatus } from "@civiclens/types";
import { healthStatusSchema } from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ApiHealthResult =
  { reachable: true; data: HealthStatus } | { reachable: false; error: string };

/**
 * Calls the backend's versioned health endpoint (docs/API.md §2, apps/api
 * `GET /api/v1/health`). Deliberately never throws — a Phase 1 goal is
 * proving the frontend degrades gracefully when the API isn't reachable,
 * not wiring real functionality (see docs/ARCHITECTURE.md §11 "everything
 * indexed is reviewed" doesn't apply yet, but the same defensive posture
 * does).
 */
export async function getApiHealth(): Promise<ApiHealthResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });

    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = healthStatusSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}
