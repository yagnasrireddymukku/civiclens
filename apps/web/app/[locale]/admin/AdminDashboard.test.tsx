import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getAdminDashboard = vi.fn();
vi.mock("@/lib/admin", () => ({
  getAdminDashboard: (...args: unknown[]) => getAdminDashboard(...args),
}));

// `@/components/civic`'s barrel re-exports sibling components (e.g.
// `SearchBar`) that pull in `@/i18n/navigation` even though this test
// only renders `VerificationStatus` — mocked here so importing the
// barrel doesn't require next-intl's real navigation setup.
vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/",
}));

import { AdminDashboard } from "./AdminDashboard";

const LABELS = {
  loading: "Loading…",
  errorGeneric: "Something went wrong. Please try again.",
  sectionPending: "Pending review",
  pendingChangeRecords: "Change records awaiting review",
  sectionDistribution: "Verification status distribution",
  sectionRecentChanges: "Recently reviewed changes",
  sectionRecentVerifications: "Recent verifications",
  noRecentChanges: "No changes have been reviewed yet.",
  noRecentVerifications: "No verifications recorded yet.",
  statusApproved: "Approved",
  statusRejected: "Rejected",
  statusPending: "Pending",
};

describe("AdminDashboard (Admin Intelligence Center)", () => {
  beforeEach(() => {
    getAdminDashboard.mockReset();
  });

  it("shows real, data-backed metrics, never a fabricated statistic", async () => {
    getAdminDashboard.mockResolvedValue({
      reachable: true,
      data: {
        pending_change_records: 3,
        verification_status_counts: { VERIFIED: 5, NEEDS_REVIEW: 2, UNVERIFIED: 1, EXPIRED: 0 },
        recent_change_decisions: [
          {
            id: "cr1",
            entity_type: "job",
            entity_id: "job1",
            field: "publication_status",
            review_status: "APPROVED",
            reviewed_by: "u1",
            applied_at: "2026-01-01T00:00:00Z",
          },
        ],
        recent_verifications: [
          {
            id: "vr1",
            entity_type: "job",
            entity_id: "job1",
            status: "VERIFIED",
            verified_by: "u1",
            verified_at: "2026-01-01T00:00:00Z",
          },
        ],
      },
    });

    render(<AdminDashboard labels={LABELS} />);

    expect(await screen.findByText("3")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });

  it("shows empty states for recent activity when there is none", async () => {
    getAdminDashboard.mockResolvedValue({
      reachable: true,
      data: {
        pending_change_records: 0,
        verification_status_counts: { VERIFIED: 0, NEEDS_REVIEW: 0, UNVERIFIED: 0, EXPIRED: 0 },
        recent_change_decisions: [],
        recent_verifications: [],
      },
    });

    render(<AdminDashboard labels={LABELS} />);

    expect(await screen.findByText("No changes have been reviewed yet.")).toBeInTheDocument();
    expect(screen.getByText("No verifications recorded yet.")).toBeInTheDocument();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    getAdminDashboard.mockResolvedValue({ reachable: false, error: "API responded with HTTP 500" });

    render(<AdminDashboard labels={LABELS} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Please try again.",
    );
  });
});
