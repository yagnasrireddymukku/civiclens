import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const LABELS: Record<string, string> = {
  "Shell.brand": "CivicLens",
  "Shell.dashboardLink": "Dashboard",
  "Shell.adminLink": "Admin",
  "Shell.userAreaSignIn": "Sign in",
  "Shell.userAreaSignOut": "Sign out",
  "Nav.comingSoonHint": "Coming soon",
  "Nav.comingSoon": "Coming soon",
};

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => LABELS[key] ?? key,
  useLocale: () => "en",
}));

const push = vi.fn();
vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ push, replace: vi.fn() }),
  usePathname: () => "/",
}));

vi.mock("@/i18n/routing", () => ({
  routing: { locales: ["en", "te"] },
}));

const signOut = vi.fn();
const useAuth = vi.fn();
vi.mock("@/components/auth", () => ({
  useAuth: () => useAuth(),
}));

import { TopNav } from "./TopNav";

describe("TopNav (Tracking + Notifications)", () => {
  beforeEach(() => {
    useAuth.mockReset();
    signOut.mockReset();
    push.mockReset();
  });

  it("shows a real sign-in link, never a disabled placeholder, when signed out", () => {
    useAuth.mockReturnValue({ user: null, loading: false, signOut });

    render(<TopNav />);

    const link = screen.getByRole("link", { name: "Sign in" });
    expect(link).toHaveAttribute("href", "/login");
    expect(link).not.toHaveAttribute("disabled");
  });

  it("shows a dashboard link and sign-out control when signed in", async () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "a@example-test.invalid",
        role: "user",
        email_notifications_enabled: false,
      },
      loading: false,
      signOut,
    });

    const user = userEvent.setup();
    render(<TopNav />);

    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute(
      "href",
      "/dashboard/tracking",
    );

    expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(signOut).toHaveBeenCalled();
    });
    expect(push).toHaveBeenCalledWith("/");
  });

  it("shows an admin link for an editor, but not an ordinary user", () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "editor@example-test.invalid",
        role: "editor",
        email_notifications_enabled: false,
      },
      loading: false,
      signOut,
    });

    render(<TopNav />);

    expect(screen.getByRole("link", { name: "Admin" })).toHaveAttribute("href", "/admin");
  });

  it("shows an admin link for an admin", () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "admin@example-test.invalid",
        role: "admin",
        email_notifications_enabled: false,
      },
      loading: false,
      signOut,
    });

    render(<TopNav />);

    expect(screen.getByRole("link", { name: "Admin" })).toHaveAttribute("href", "/admin");
  });

  it("renders neither sign-in nor sign-out while auth state is loading", () => {
    useAuth.mockReturnValue({ user: null, loading: true, signOut });

    render(<TopNav />);

    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
  });
});
