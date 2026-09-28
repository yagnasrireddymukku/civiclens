import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getCurrentUser = vi.fn();
const refreshSession = vi.fn();
const login = vi.fn();
const registerAccount = vi.fn();
const logout = vi.fn();
const getCsrfToken = vi.fn(() => "cookie-csrf-token");

vi.mock("@/lib/auth", () => ({
  getCurrentUser: (...args: unknown[]) => getCurrentUser(...args),
  refreshSession: (...args: unknown[]) => refreshSession(...args),
  login: (...args: unknown[]) => login(...args),
  registerAccount: (...args: unknown[]) => registerAccount(...args),
  logout: (...args: unknown[]) => logout(...args),
  getCsrfToken: () => getCsrfToken(),
}));

import { AuthProvider, useAuth } from "./AuthProvider";

function Probe() {
  const { user, csrfToken, loading } = useAuth();
  if (loading) return <p>loading</p>;
  return <p>{user ? `signed in: ${user.email} (csrf: ${csrfToken})` : "signed out"}</p>;
}

const USER = {
  id: "u1",
  email: "a@example-test.invalid",
  role: "user" as const,
  email_notifications_enabled: false,
};

describe("AuthProvider (Tracking + Notifications)", () => {
  beforeEach(() => {
    getCurrentUser.mockReset();
    refreshSession.mockReset();
    login.mockReset();
    registerAccount.mockReset();
    logout.mockReset();
    getCsrfToken.mockReset().mockReturnValue("cookie-csrf-token");
  });

  it("loads the current user from an existing session on mount", async () => {
    getCurrentUser.mockResolvedValue({ reachable: true, data: USER });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    expect(screen.getByText("loading")).toBeInTheDocument();
    expect(
      await screen.findByText("signed in: a@example-test.invalid (csrf: cookie-csrf-token)"),
    ).toBeInTheDocument();
    expect(refreshSession).not.toHaveBeenCalled();
  });

  it("silently refreshes an expired access token before declaring the user signed out", async () => {
    getCurrentUser.mockResolvedValue({ reachable: true, data: null });
    refreshSession.mockResolvedValue({
      reachable: true,
      data: { user: USER, csrf_token: "refreshed-csrf" },
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    expect(
      await screen.findByText("signed in: a@example-test.invalid (csrf: refreshed-csrf)"),
    ).toBeInTheDocument();
  });

  it("reports signed out when both the session and the silent refresh fail", async () => {
    getCurrentUser.mockResolvedValue({ reachable: true, data: null });
    refreshSession.mockResolvedValue({ reachable: true, data: null, status: 401 });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    expect(await screen.findByText("signed out")).toBeInTheDocument();
  });

  it("updates state after a successful sign-out", async () => {
    getCurrentUser.mockResolvedValue({ reachable: true, data: USER });
    logout.mockResolvedValue({ ok: true });

    function SignOutProbe() {
      const { user, signOut } = useAuth();
      return (
        <div>
          <p>{user ? "signed in" : "signed out"}</p>
          <button onClick={() => void signOut()}>sign out</button>
        </div>
      );
    }

    const user = userEvent.setup();
    render(
      <AuthProvider>
        <SignOutProbe />
      </AuthProvider>,
    );

    expect(await screen.findByText("signed in")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "sign out" }));

    await waitFor(() => {
      expect(logout).toHaveBeenCalledWith("cookie-csrf-token");
    });
    expect(screen.getByText("signed out")).toBeInTheDocument();
  });
});
