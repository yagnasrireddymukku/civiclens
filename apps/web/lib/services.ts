import type {
  DeliveryMode,
  ServiceCategory,
  ServiceDetail,
  ServiceListResponse,
} from "@civiclens/types";
import { serviceDetailSchema, serviceListResponseSchema } from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ServiceListParams {
  page?: number;
  category?: ServiceCategory;
  deliveryMode?: DeliveryMode;
}

export type ServiceListApiResult =
  { reachable: true; data: ServiceListResponse } | { reachable: false; error: string };

export type ServiceDetailApiResult =
  | { reachable: true; data: ServiceDetail }
  | { reachable: false; error: string }
  | { reachable: true; data: null };

/**
 * Calls the backend's `GET /api/v1/services` (docs/API.md §14,
 * docs/DATABASE.md §11). Deliberately never throws — same defensive
 * posture as `getApiHealth`/`getJobs` (lib/api.ts, lib/jobs.ts).
 */
export async function getServices({
  page = 1,
  category,
  deliveryMode,
}: ServiceListParams): Promise<ServiceListApiResult> {
  try {
    const query = new URLSearchParams({ page: String(page) });
    if (category) query.set("category", category);
    if (deliveryMode) query.set("delivery_mode", deliveryMode);

    const response = await fetch(`${API_BASE_URL}/api/v1/services?${query.toString()}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = serviceListResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

/**
 * Calls `GET /api/v1/services/{slug}`. A 404 is not an error state — it
 * means "no such service" (or, indistinguishably to the public, "not
 * yet published") and is reported as `{ reachable: true; data: null }`
 * so callers can render a not-found page rather than an error banner.
 */
export async function getServiceBySlug(slug: string): Promise<ServiceDetailApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/services/${encodeURIComponent(slug)}`, {
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
    const data = serviceDetailSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}
