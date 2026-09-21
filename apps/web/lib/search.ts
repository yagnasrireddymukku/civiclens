import type { SearchResponse } from "@civiclens/types";
import { searchResponseSchema } from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SearchParams {
  q: string;
  locale: string;
  page?: number;
}

export type SearchApiResult =
  { reachable: true; data: SearchResponse } | { reachable: false; error: string };

/**
 * Calls the backend's `GET /api/v1/search` (docs/API.md, docs/SEARCH.md).
 * Deliberately never throws — same defensive posture as `getApiHealth`
 * (lib/api.ts): a search page must degrade to an honest error state,
 * not crash, when the API is unreachable.
 */
export async function getSearchResults({
  q,
  locale,
  page = 1,
}: SearchParams): Promise<SearchApiResult> {
  try {
    const query = new URLSearchParams({ q, locale, page: String(page) });
    const response = await fetch(`${API_BASE_URL}/api/v1/search?${query.toString()}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = searchResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}
