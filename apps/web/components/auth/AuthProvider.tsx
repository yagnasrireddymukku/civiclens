"use client";

import type { AuthUser } from "@civiclens/types";
import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  getCsrfToken,
  getCurrentUser,
  login,
  logout,
  refreshSession,
  registerAccount,
} from "@/lib/auth";

interface AuthContextValue {
  user: AuthUser | null;
  csrfToken: string | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ ok: true } | { ok: false; error: string }>;
  signUp: (email: string, password: string) => Promise<{ ok: true } | { ok: false; error: string }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * The single source of truth for "who is signed in," loaded once on
 * mount and updated by sign-in/sign-up/sign-out. Session state itself
 * lives only in httpOnly cookies (docs/FRONTEND.md §5) — this context
 * holds nothing but a read-only mirror of it (the current user, plus
 * the non-httpOnly CSRF token needed to attach `X-CSRF-Token` to
 * mutating requests) for the pieces of UI that need to know.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      const result = await getCurrentUser();
      if (cancelled) return;

      if (result.reachable && result.data) {
        setUser(result.data);
        setCsrfToken(getCsrfToken());
        setLoading(false);
        return;
      }

      // No session found — the access-token cookie may simply have
      // expired while a still-valid refresh token remains. One silent
      // refresh attempt recovers that case without forcing re-login;
      // any other outcome (never signed in, refresh token also
      // expired/revoked) is a genuine signed-out state.
      const refreshed = await refreshSession();
      if (cancelled) return;

      if (refreshed.reachable && refreshed.data) {
        setUser(refreshed.data.user);
        setCsrfToken(refreshed.data.csrf_token);
      } else {
        setUser(null);
        setCsrfToken(null);
      }
      setLoading(false);
    }

    void loadSession();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await login(email, password);
    if (result.reachable && result.data) {
      setUser(result.data.user);
      setCsrfToken(result.data.csrf_token);
      return { ok: true as const };
    }
    if (!result.reachable) return { ok: false as const, error: result.error };
    return { ok: false as const, error: "Incorrect email or password." };
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    const result = await registerAccount(email, password);
    if (result.reachable && result.data) {
      setUser(result.data.user);
      setCsrfToken(result.data.csrf_token);
      return { ok: true as const };
    }
    if (!result.reachable) return { ok: false as const, error: result.error };
    if ("status" in result && result.status === 409) {
      return { ok: false as const, error: "An account with this email already exists." };
    }
    return { ok: false as const, error: "Could not create an account with those details." };
  }, []);

  const signOut = useCallback(async () => {
    if (csrfToken) await logout(csrfToken);
    setUser(null);
    setCsrfToken(null);
  }, [csrfToken]);

  const value = useMemo(
    () => ({ user, csrfToken, loading, signIn, signUp, signOut }),
    [user, csrfToken, loading, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
