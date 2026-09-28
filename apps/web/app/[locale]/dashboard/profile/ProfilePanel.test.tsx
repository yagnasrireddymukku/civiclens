import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const signOut = vi.fn();
const useAuth = vi.fn();
vi.mock("@/components/auth", () => ({
  useAuth: () => useAuth(),
}));

const push = vi.fn();
vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push }),
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const updateNotificationPreference = vi.fn();
vi.mock("@/lib/auth", () => ({
  updateNotificationPreference: (...args: unknown[]) => updateNotificationPreference(...args),
}));

import { ProfilePanel } from "./ProfilePanel";

const LABELS = {
  loading: "Loading your profile…",
  signInTitle: "Sign in to see your profile",
  signInCta: "Sign in",
  emailLabel: "Email",
  roleLabel: "Role",
  emailNotificationsLabel: "Email notifications",
  emailNotificationsHint: "When enabled, CivicLens may also email you.",
  saveButton: "Save",
  savedMessage: "Saved.",
  errorGeneric: "Something went wrong. Please try again.",
  signOutButton: "Sign out",
};

describe("ProfilePanel (Tracking + Notifications)", () => {
  beforeEach(() => {
    useAuth.mockReset();
    signOut.mockReset();
    push.mockReset();
    updateNotificationPreference.mockReset();
  });

  it("prompts sign-in when signed out", () => {
    useAuth.mockReturnValue({ user: null, csrfToken: null, loading: false, signOut });

    render(<ProfilePanel labels={LABELS} />);

    expect(screen.getByText("Sign in to see your profile")).toBeInTheDocument();
  });

  it("shows the account's email and role", () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "a@example-test.invalid",
        role: "user",
        email_notifications_enabled: false,
      },
      csrfToken: "csrf-token",
      loading: false,
      signOut,
    });

    render(<ProfilePanel labels={LABELS} />);

    expect(screen.getByText("a@example-test.invalid")).toBeInTheDocument();
    expect(screen.getByText("user")).toBeInTheDocument();
  });

  it("saves the email notification preference and confirms it", async () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "a@example-test.invalid",
        role: "user",
        email_notifications_enabled: false,
      },
      csrfToken: "csrf-token",
      loading: false,
      signOut,
    });
    updateNotificationPreference.mockResolvedValue({
      reachable: true,
      data: {
        user: {
          id: "u1",
          email: "a@example-test.invalid",
          role: "user",
          email_notifications_enabled: true,
        },
        csrf_token: "csrf-token",
      },
    });

    const user = userEvent.setup();
    render(<ProfilePanel labels={LABELS} />);

    await user.click(screen.getByLabelText("Email notifications"));
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(updateNotificationPreference).toHaveBeenCalledWith("csrf-token", true);
    });
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
  });

  it("signs out and returns to the home page", async () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "a@example-test.invalid",
        role: "user",
        email_notifications_enabled: false,
      },
      csrfToken: "csrf-token",
      loading: false,
      signOut,
    });

    const user = userEvent.setup();
    render(<ProfilePanel labels={LABELS} />);

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(signOut).toHaveBeenCalled();
    });
    expect(push).toHaveBeenCalledWith("/");
  });
});
