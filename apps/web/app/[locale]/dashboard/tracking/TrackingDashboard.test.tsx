import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const useAuth = vi.fn();
vi.mock("@/components/auth", () => ({
  useAuth: () => useAuth(),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const getTrackedItems = vi.fn();
const pauseTrackedItem = vi.fn();
const resumeTrackedItem = vi.fn();
const removeTrackedItem = vi.fn();
vi.mock("@/lib/tracking", () => ({
  getTrackedItems: (...args: unknown[]) => getTrackedItems(...args),
  pauseTrackedItem: (...args: unknown[]) => pauseTrackedItem(...args),
  resumeTrackedItem: (...args: unknown[]) => resumeTrackedItem(...args),
  removeTrackedItem: (...args: unknown[]) => removeTrackedItem(...args),
}));

const getNotifications = vi.fn();
const markNotificationRead = vi.fn();
const markAllNotificationsRead = vi.fn();
vi.mock("@/lib/notifications", () => ({
  getNotifications: (...args: unknown[]) => getNotifications(...args),
  markNotificationRead: (...args: unknown[]) => markNotificationRead(...args),
  markAllNotificationsRead: (...args: unknown[]) => markAllNotificationsRead(...args),
}));

import { TrackingDashboard } from "./TrackingDashboard";

const LABELS = {
  loading: "Loading your dashboard…",
  signInTitle: "Sign in to see your dashboard",
  signInBody: "Track jobs, schemes, services, and documents.",
  signInCta: "Sign in",
  sectionDeadlines: "Upcoming deadlines",
  noDeadlines: "No upcoming deadlines among the items you're tracking.",
  sectionTrackedItems: "Tracked items",
  sectionNotifications: "Notifications",
  errorGeneric: "Something went wrong loading your dashboard. Please try again.",
  trackedEmptyState: "You aren't tracking anything yet.",
  statusActive: "Tracking",
  statusPaused: "Paused",
  pauseAction: "Pause",
  resumeAction: "Resume",
  removeAction: "Remove",
  deadlineLabel: "Deadline",
  unavailableNotice: "This item is no longer published on CivicLens.",
  notificationsEmptyState: "No notifications yet.",
  markAllRead: "Mark all as read",
  markRead: "Mark as read",
  unreadBadge: "unread",
  typeDeadlineReminder: "Deadline reminder",
  typeChangeDetected: "Update",
  typeEntityUnavailable: "No longer available",
};

const TRACKED_ITEM = {
  id: "tracked-1",
  entity_type: "job" as const,
  title: "Test Job",
  route: "/jobs/test-job",
  verification_status: "VERIFIED" as const,
  last_verified: null,
  source_organization: null,
  still_available: true,
  label: null,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  deadline: "2026-12-31",
  deadline_expired: false,
};

const NOTIFICATION = {
  id: "notif-1",
  notification_type: "CHANGE_DETECTED" as const,
  title: "Update: publication status changed",
  body: "Publication status changed from 'DRAFT' to 'PUBLISHED'.",
  entity_type: "job",
  entity_id: "job-1",
  created_at: "2026-01-01T00:00:00Z",
  read_at: null,
};

describe("TrackingDashboard (Tracking + Notifications)", () => {
  beforeEach(() => {
    useAuth.mockReset();
    getTrackedItems.mockReset();
    getNotifications.mockReset();
    pauseTrackedItem.mockReset();
    removeTrackedItem.mockReset();
    markNotificationRead.mockReset();
    markAllNotificationsRead.mockReset();
  });

  it("prompts sign-in when signed out, without fetching private data", () => {
    useAuth.mockReturnValue({ user: null, csrfToken: null, loading: false });

    render(<TrackingDashboard locale="en" labels={LABELS} />);

    expect(screen.getByText("Sign in to see your dashboard")).toBeInTheDocument();
    expect(getTrackedItems).not.toHaveBeenCalled();
    expect(getNotifications).not.toHaveBeenCalled();
  });

  it("shows tracked items, an upcoming deadline, and the notification inbox", async () => {
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
    getTrackedItems.mockResolvedValue({ reachable: true, data: { results: [TRACKED_ITEM] } });
    getNotifications.mockResolvedValue({
      reachable: true,
      data: {
        results: [NOTIFICATION],
        pagination: { page: 1, page_size: 20, total_count: 1 },
        unread_count: 1,
      },
    });

    render(<TrackingDashboard locale="en" labels={LABELS} />);

    expect(await screen.findAllByText("Test Job")).not.toHaveLength(0);
    expect(screen.getByText("Update: publication status changed")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument(); // unread badge
  });

  it("shows an empty state for tracked items and notifications when there are none", async () => {
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
    getNotifications.mockResolvedValue({
      reachable: true,
      data: {
        results: [],
        pagination: { page: 1, page_size: 20, total_count: 0 },
        unread_count: 0,
      },
    });

    render(<TrackingDashboard locale="en" labels={LABELS} />);

    expect(await screen.findByText("You aren't tracking anything yet.")).toBeInTheDocument();
    expect(screen.getByText("No notifications yet.")).toBeInTheDocument();
    expect(
      screen.getByText("No upcoming deadlines among the items you're tracking."),
    ).toBeInTheDocument();
  });

  it("pauses a tracked item and reflects the new status", async () => {
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
    getTrackedItems.mockResolvedValue({ reachable: true, data: { results: [TRACKED_ITEM] } });
    getNotifications.mockResolvedValue({
      reachable: true,
      data: {
        results: [],
        pagination: { page: 1, page_size: 20, total_count: 0 },
        unread_count: 0,
      },
    });
    pauseTrackedItem.mockResolvedValue({ ok: true });

    const user = userEvent.setup();
    render(<TrackingDashboard locale="en" labels={LABELS} />);

    const pauseButton = await screen.findByRole("button", { name: "Pause" });
    await user.click(pauseButton);

    await waitFor(() => {
      expect(pauseTrackedItem).toHaveBeenCalledWith("csrf-token", "tracked-1");
    });
    expect(await screen.findByRole("button", { name: "Resume" })).toBeInTheDocument();
  });

  it("marks a notification as read", async () => {
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
    getNotifications.mockResolvedValue({
      reachable: true,
      data: {
        results: [NOTIFICATION],
        pagination: { page: 1, page_size: 20, total_count: 1 },
        unread_count: 1,
      },
    });
    markNotificationRead.mockResolvedValue({
      ok: true,
      data: { ...NOTIFICATION, read_at: "2026-01-02T00:00:00Z" },
    });

    const user = userEvent.setup();
    render(<TrackingDashboard locale="en" labels={LABELS} />);

    const markReadButton = await screen.findByRole("button", { name: "Mark as read" });
    await user.click(markReadButton);

    await waitFor(() => {
      expect(markNotificationRead).toHaveBeenCalledWith("csrf-token", "notif-1");
    });
    expect(screen.queryByRole("button", { name: "Mark as read" })).not.toBeInTheDocument();
  });
});
