import type { AuthResponse, AuthUser } from "@civiclens/types";
import { authResponseSchema, authUserSchema } from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CSRF_COOKIE_NAME = "civiclens_csrf";

export type AuthApiResult =
  | { reachable: true; data: AuthResponse }
  | { reachable: false; error: string }
  | { reachable: true; data: null; status: number };

export type CurrentUserApiResult =
  | { reachable: true; data: AuthUser }
  | { reachable: false; error: string }
  | { reachable: true; data: null };

export type AuthActionResult = { ok: true } | { ok: false; error: string };

/**
 * The CSRF token is a plain, non-httpOnly cookie by design (the double-
 * submit pattern, docs/SECURITY.md §2) — readable here so a page loaded
 * with an existing session (cookie already set from a prior visit, no
 * fresh register/login response in hand) can still attach
 * `X-CSRF-Token` to a mutating request. Client-side only; returns `null`
 * during server rendering or when no session cookie is present.
 */
export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${CSRF_COOKIE_NAME}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Calls `GET /api/v1/auth/me`. A 401 is not an error state — it means
 * "no session" and is reported as `{ reachable: true; data: null }` so
 * callers can render a signed-out state rather than an error banner,
 * mirroring `getJobBySlug`'s 404-is-not-an-error convention.
 */
export async function getCurrentUser(): Promise<CurrentUserApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
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
    const data = authUserSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

export async function registerAccount(email: string, password: string): Promise<AuthApiResult> {
  return authRequest("/api/v1/auth/register", { email, password });
}

export async function login(email: string, password: string): Promise<AuthApiResult> {
  return authRequest("/api/v1/auth/login", { email, password });
}

/**
 * `POST /api/v1/auth/refresh` — rotates the refresh token (reads it
 * from the httpOnly cookie, no body). Used once, silently, when a page
 * loads and `getCurrentUser` reports "no session": the access token
 * (15 min TTL) may simply have expired while a still-valid refresh
 * token (30 day TTL) remains, and this recovers the session without
 * forcing a re-login. A genuinely expired/absent refresh token also
 * 401s here, which callers treat the same as "signed out."
 */
export async function refreshSession(): Promise<AuthApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
      signal: AbortSignal.timeout(5000),
    });

    if (response.status === 401) {
      return { reachable: true, data: null, status: 401 };
    }
    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = authResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

async function authRequest(path: string, body: Record<string, unknown>): Promise<AuthApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 409 || response.status === 422) {
        return { reachable: true, data: null, status: response.status };
      }
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = authResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

/**
 * `POST /api/v1/auth/logout` — requires the CSRF header (a mutating,
 * cookie-clearing request). Deliberately tolerant of failure: a logout
 * that can't reach the API still clears client-visible state (the
 * caller drops its in-memory user) rather than trapping the user in a
 * "can't sign out" state.
 */
export async function logout(csrfToken: string): Promise<AuthActionResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
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

export async function updateNotificationPreference(
  csrfToken: string,
  emailNotificationsEnabled: boolean,
): Promise<AuthApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify({ email_notifications_enabled: emailNotificationsEnabled }),
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = authUserSchema.parse(payload);
    return { reachable: true, data: { user: data, csrf_token: csrfToken } };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}
