import type { EmploymentType, JobDetail, JobListResponse } from "@civiclens/types";
import { jobDetailSchema, jobListResponseSchema } from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface JobListParams {
  page?: number;
  employmentType?: EmploymentType;
  status?: string;
}

export type JobListApiResult =
  { reachable: true; data: JobListResponse } | { reachable: false; error: string };

export type JobDetailApiResult =
  | { reachable: true; data: JobDetail }
  | { reachable: false; error: string }
  | { reachable: true; data: null };

/**
 * Calls the backend's `GET /api/v1/jobs` (docs/API.md, docs/DATABASE.md
 * §2.3/§8). Deliberately never throws — same defensive posture as
 * `getApiHealth`/`getSearchResults` (lib/api.ts, lib/search.ts).
 */
export async function getJobs({
  page = 1,
  employmentType,
  status,
}: JobListParams): Promise<JobListApiResult> {
  try {
    const query = new URLSearchParams({ page: String(page) });
    if (employmentType) query.set("employment_type", employmentType);
    if (status) query.set("status", status);

    const response = await fetch(`${API_BASE_URL}/api/v1/jobs?${query.toString()}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = jobListResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

/**
 * Calls `GET /api/v1/jobs/{slug}`. A 404 is not an error state — it
 * means "no such job" (or, indistinguishably to the public, "not yet
 * published") and is reported as `{ reachable: true; data: null }` so
 * callers can render a not-found page rather than an error banner.
 */
export async function getJobBySlug(slug: string): Promise<JobDetailApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${encodeURIComponent(slug)}`, {
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
    const data = jobDetailSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}
