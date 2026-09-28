import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const useAuth = vi.fn();
vi.mock("@/components/auth", () => ({
  useAuth: () => useAuth(),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

import { AdminGate } from "./AdminGate";

const LABELS = {
  loading: "Loading…",
  signInTitle: "Sign in to continue",
  signInCta: "Sign in",
  notAuthorizedTitle: "Not authorized",
  notAuthorizedBody: "Your account does not have access to the admin console.",
};

describe("AdminGate (Admin Intelligence Center)", () => {
  it("renders nothing but a loading state while auth is resolving", () => {
    useAuth.mockReturnValue({ user: null, loading: true });

    render(
      <AdminGate labels={LABELS}>
        <p>secret admin content</p>
      </AdminGate>,
    );

    expect(screen.getAllByText("Loading…").length).toBeGreaterThan(0);
    expect(screen.queryByText("secret admin content")).not.toBeInTheDocument();
  });

  it("prompts sign-in when signed out", () => {
    useAuth.mockReturnValue({ user: null, loading: false });

    render(
      <AdminGate labels={LABELS}>
        <p>secret admin content</p>
      </AdminGate>,
    );

    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
    expect(screen.queryByText("secret admin content")).not.toBeInTheDocument();
  });

  it("shows a not-authorized message for an ordinary signed-in user, never the admin content", () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "a@example-test.invalid",
        role: "user",
        email_notifications_enabled: false,
      },
      loading: false,
    });

    render(
      <AdminGate labels={LABELS}>
        <p>secret admin content</p>
      </AdminGate>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Not authorized");
    expect(screen.queryByText("secret admin content")).not.toBeInTheDocument();
  });

  it("renders the admin content for an editor", () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "editor@example-test.invalid",
        role: "editor",
        email_notifications_enabled: false,
      },
      loading: false,
    });

    render(
      <AdminGate labels={LABELS}>
        <p>secret admin content</p>
      </AdminGate>,
    );

    expect(screen.getByText("secret admin content")).toBeInTheDocument();
  });

  it("renders the admin content for an admin", () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "admin@example-test.invalid",
        role: "admin",
        email_notifications_enabled: false,
      },
      loading: false,
    });

    render(
      <AdminGate labels={LABELS}>
        <p>secret admin content</p>
      </AdminGate>,
    );

    expect(screen.getByText("secret admin content")).toBeInTheDocument();
  });
});
