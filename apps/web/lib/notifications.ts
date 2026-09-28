import type { NotificationItem, NotificationListResponse } from "@civiclens/types";
import { notificationItemSchema, notificationListResponseSchema } from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type NotificationListApiResult =
  | { reachable: true; data: NotificationListResponse }
  | { reachable: false; error: string }
  | { reachable: true; data: null }; // 401 — not signed in

export type NotificationActionResult =
  { ok: true; data: NotificationItem } | { ok: false; error: string };

/**
 * `GET /api/v1/notifications` — the caller's own inbox only. A 401
 * means "not signed in," reported as `{ reachable: true; data: null }`
 * so the inbox can render a sign-in prompt rather than an error banner
 * (same convention as `getTrackedItems`).
 */
export async function getNotifications(
  page = 1,
  pageSize = 20,
): Promise<NotificationListApiResult> {
  try {
    const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    const response = await fetch(`${API_BASE_URL}/api/v1/notifications?${query.toString()}`, {
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
    const data = notificationListResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

export async function markNotificationRead(
  csrfToken: string,
  id: string,
): Promise<NotificationActionResult> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/notifications/${encodeURIComponent(id)}/read`,
      {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRF-Token": csrfToken },
        signal: AbortSignal.timeout(5000),
      },
    );

    if (!response.ok) {
      return { ok: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = notificationItemSchema.parse(payload);
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown error" };
  }
}

export async function markAllNotificationsRead(
  csrfToken: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/notifications/read-all`, {
      method: "POST",
      credentials: "include",
      headers: { "X-CSRF-Token": csrfToken },
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok && response.status !== 204) {
      return { ok: false, error: `API responded with HTTP ${response.status}` };
    }
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown error" };
  }
}
