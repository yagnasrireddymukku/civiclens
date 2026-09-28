import type { TrackedEntityType, TrackedItem, TrackedItemListResponse } from "@civiclens/types";
import { trackedItemListResponseSchema, trackedItemSchema } from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type TrackingListApiResult =
  | { reachable: true; data: TrackedItemListResponse }
  | { reachable: false; error: string }
  | { reachable: true; data: null }; // 401 — not signed in

export type TrackingItemApiResult =
  { reachable: true; data: TrackedItem } | { reachable: false; error: string; status?: number };

export type TrackingActionResult = { ok: true } | { ok: false; error: string; status?: number };

/**
 * `GET /api/v1/tracking` — the caller's own tracked items only (the
 * backend never accepts a user id; ownership comes entirely from the
 * session cookie). A 401 means "not signed in," reported as
 * `{ reachable: true; data: null }` so the dashboard can render a
 * sign-in prompt rather than an error banner.
 */
export async function getTrackedItems(): Promise<TrackingListApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/tracking`, {
      credentials: "include",
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (response.status === 401) {
      return { reachable: true, data: null };
    }
    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = trackedItemListResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

export async function trackEntity(
  csrfToken: string,
  entityType: TrackedEntityType,
  entitySlug: string,
  label?: string,
): Promise<TrackingItemApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/tracking`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify({
        entity_type: entityType,
        entity_slug: entitySlug,
        label: label ?? null,
      }),
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return {
        reachable: false,
        error: `API responded with HTTP ${response.status}`,
        status: response.status,
      };
    }

    const payload: unknown = await response.json();
    const data = trackedItemSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

export async function pauseTrackedItem(
  csrfToken: string,
  id: string,
): Promise<TrackingActionResult> {
  return trackingAction(`/api/v1/tracking/${encodeURIComponent(id)}/pause`, "POST", csrfToken);
}

export async function resumeTrackedItem(
  csrfToken: string,
  id: string,
): Promise<TrackingActionResult> {
  return trackingAction(`/api/v1/tracking/${encodeURIComponent(id)}/resume`, "POST", csrfToken);
}

export async function removeTrackedItem(
  csrfToken: string,
  id: string,
): Promise<TrackingActionResult> {
  return trackingAction(`/api/v1/tracking/${encodeURIComponent(id)}`, "DELETE", csrfToken);
}

async function trackingAction(
  path: string,
  method: "POST" | "DELETE",
  csrfToken: string,
): Promise<TrackingActionResult> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      credentials: "include",
      headers: { "X-CSRF-Token": csrfToken },
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok && response.status !== 204) {
      return {
        ok: false,
        error: `API responded with HTTP ${response.status}`,
        status: response.status,
      };
    }
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown error" };
  }
}
