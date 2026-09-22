import type { SchemeCategory, SchemeDetail, SchemeListResponse } from "@civiclens/types";
import { schemeDetailSchema, schemeListResponseSchema } from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SchemeListParams {
  page?: number;
  category?: SchemeCategory;
}

export type SchemeListApiResult =
  { reachable: true; data: SchemeListResponse } | { reachable: false; error: string };

export type SchemeDetailApiResult =
  | { reachable: true; data: SchemeDetail }
  | { reachable: false; error: string }
  | { reachable: true; data: null };

/**
 * Calls the backend's `GET /api/v1/schemes` (docs/API.md §15,
 * docs/DATABASE.md §13). Deliberately never throws — same defensive
 * posture as `getApiHealth`/`getJobs`/`getServices` (lib/api.ts,
 * lib/jobs.ts, lib/services.ts).
 */
export async function getSchemes({
  page = 1,
  category,
}: SchemeListParams): Promise<SchemeListApiResult> {
  try {
    const query = new URLSearchParams({ page: String(page) });
    if (category) query.set("category", category);

    const response = await fetch(`${API_BASE_URL}/api/v1/schemes?${query.toString()}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = schemeListResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

/**
 * Calls `GET /api/v1/schemes/{slug}`. A 404 is not an error state — it
 * means "no such scheme" (or, indistinguishably to the public, "not yet
 * published") and is reported as `{ reachable: true; data: null }` so
 * callers can render a not-found page rather than an error banner.
 */
export async function getSchemeBySlug(slug: string): Promise<SchemeDetailApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/schemes/${encodeURIComponent(slug)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (response.status === 404) {
      return { reachable: true, data: null };
    }
    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = schemeDetailSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}
