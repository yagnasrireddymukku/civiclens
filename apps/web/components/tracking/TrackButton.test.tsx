import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const LABELS: Record<string, string> = {
  signInToTrack: "Sign in to track this",
  trackThis: "Track this",
  stopTracking: "Stop tracking",
  errorGeneric: "Something went wrong. Please try again.",
};

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => LABELS[key] ?? key,
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const useAuth = vi.fn();
vi.mock("@/components/auth", () => ({
  useAuth: () => useAuth(),
}));

const getTrackedItems = vi.fn();
const trackEntity = vi.fn();
const removeTrackedItem = vi.fn();
vi.mock("@/lib/tracking", () => ({
  getTrackedItems: (...args: unknown[]) => getTrackedItems(...args),
  trackEntity: (...args: unknown[]) => trackEntity(...args),
  removeTrackedItem: (...args: unknown[]) => removeTrackedItem(...args),
}));

import { TrackButton } from "./TrackButton";

describe("TrackButton (Tracking + Notifications)", () => {
  beforeEach(() => {
    useAuth.mockReset();
    getTrackedItems.mockReset();
    trackEntity.mockReset();
    removeTrackedItem.mockReset();
  });

  it("shows a sign-in link, never a disabled placeholder, when signed out", () => {
    useAuth.mockReturnValue({ user: null, csrfToken: null, loading: false });

    render(<TrackButton entityType="job" entitySlug="test-job" />);

    const link = screen.getByRole("link", { name: "Sign in to track this" });
    expect(link).toHaveAttribute("href", "/login");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders nothing while the auth state is still loading", () => {
    useAuth.mockReturnValue({ user: null, csrfToken: null, loading: true });

    const { container } = render(<TrackButton entityType="job" entitySlug="test-job" />);

    expect(container).toBeEmptyDOMElement();
  });

  it("offers to track an entity the signed-in user isn't tracking yet", async () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "a@example-test.invalid",
        role: "user",
        email_notifications_enabled: false,
      },
      csrfToken: "csrf-token",
      loading: false,
    });
    getTrackedItems.mockResolvedValue({ reachable: true, data: { results: [] } });
    trackEntity.mockResolvedValue({
      reachable: true,
      data: { id: "tracked-1", entity_type: "job", still_available: true },
    });

    const user = userEvent.setup();
    render(<TrackButton entityType="job" entitySlug="test-job" />);

    const trackButton = await screen.findByRole("button", { name: "Track this" });
    await user.click(trackButton);

    await waitFor(() => {
      expect(trackEntity).toHaveBeenCalledWith("csrf-token", "job", "test-job");
    });
    expect(await screen.findByRole("button", { name: "Stop tracking" })).toBeInTheDocument();
  });

  it("recognizes an entity the user is already tracking and offers to remove it", async () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "a@example-test.invalid",
        role: "user",
        email_notifications_enabled: false,
      },
      csrfToken: "csrf-token",
      loading: false,
    });
    getTrackedItems.mockResolvedValue({
      reachable: true,
      data: {
        results: [
          {
            id: "tracked-1",
            entity_type: "job",
            title: "Test Job",
            route: "/jobs/test-job",
            verification_status: "VERIFIED",
            last_verified: null,
            source_organization: null,
            still_available: true,
            label: null,
            is_active: true,
            created_at: "2026-01-01T00:00:00Z",
            deadline: null,
            deadline_expired: null,
          },
        ],
      },
    });
    removeTrackedItem.mockResolvedValue({ ok: true });

    const user = userEvent.setup();
    render(<TrackButton entityType="job" entitySlug="test-job" />);

    const removeButton = await screen.findByRole("button", { name: "Stop tracking" });
    await user.click(removeButton);

    await waitFor(() => {
      expect(removeTrackedItem).toHaveBeenCalledWith("csrf-token", "tracked-1");
    });
    expect(await screen.findByRole("button", { name: "Track this" })).toBeInTheDocument();
  });

  it("shows an error message, not a crash, when tracking fails", async () => {
    useAuth.mockReturnValue({
      user: {
        id: "u1",
        email: "a@example-test.invalid",
        role: "user",
        email_notifications_enabled: false,
      },
      csrfToken: "csrf-token",
      loading: false,
    });
    getTrackedItems.mockResolvedValue({ reachable: true, data: { results: [] } });
    trackEntity.mockResolvedValue({ reachable: false, error: "API responded with HTTP 500" });

    const user = userEvent.setup();
    render(<TrackButton entityType="job" entitySlug="test-job" />);

    const trackButton = await screen.findByRole("button", { name: "Track this" });
    await user.click(trackButton);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Please try again.",
    );
  });
});
