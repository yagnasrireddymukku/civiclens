import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const useAuth = vi.fn(() => ({ csrfToken: "csrf-token" }));
vi.mock("@/components/auth", () => ({
  useAuth: () => useAuth(),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const getChangeRecords = vi.fn();
const approveChangeRecord = vi.fn();
const rejectChangeRecord = vi.fn();
vi.mock("@/lib/admin", () => ({
  getChangeRecords: (...args: unknown[]) => getChangeRecords(...args),
  approveChangeRecord: (...args: unknown[]) => approveChangeRecord(...args),
  rejectChangeRecord: (...args: unknown[]) => rejectChangeRecord(...args),
}));

import { ChangeRecordsReview } from "./ChangeRecordsReview";

const LABELS = {
  loading: "Loading…",
  errorGeneric: "Something went wrong. Please try again.",
  emptyState: "No change records match this filter.",
  filterLabel: "Filter by status",
  filterAll: "All",
  filterPending: "Pending",
  filterApproved: "Approved",
  filterRejected: "Rejected",
  fieldChanged: "Field changed",
  detectedOn: "Detected on",
  unavailableEntity: "This item is no longer available.",
  approveAction: "Approve",
  rejectAction: "Reject",
  statusPending: "Pending",
  statusApproved: "Approved",
  statusRejected: "Rejected",
};

const PENDING_RECORD = {
  id: "cr1",
  entity_type: "job",
  entity_id: "job1",
  field: "publication_status",
  old_value: "DRAFT",
  new_value: "PUBLISHED",
  detected_at: "2026-01-01T00:00:00Z",
  review_status: "PENDING" as const,
  reviewed_by: null,
  applied_at: null,
  entity: {
    title: "Test Job",
    route: "/jobs/test-job",
    verification_status: "VERIFIED" as const,
    source_organization: "Test Board",
  },
};

describe("ChangeRecordsReview (Admin Intelligence Center)", () => {
  beforeEach(() => {
    getChangeRecords.mockReset();
    approveChangeRecord.mockReset();
    rejectChangeRecord.mockReset();
  });

  it("shows the pending queue with approve/reject actions", async () => {
    getChangeRecords.mockResolvedValue({
      reachable: true,
      data: { results: [PENDING_RECORD], pagination: { page: 1, page_size: 20, total_count: 1 } },
    });

    render(<ChangeRecordsReview locale="en" labels={LABELS} />);

    expect(await screen.findByText("Test Job")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
  });

  it("approves a record and removes the approve/reject actions once decided", async () => {
    getChangeRecords.mockResolvedValue({
      reachable: true,
      data: { results: [PENDING_RECORD], pagination: { page: 1, page_size: 20, total_count: 1 } },
    });
    approveChangeRecord.mockResolvedValue({
      reachable: true,
      data: { ...PENDING_RECORD, review_status: "APPROVED", applied_at: "2026-01-02T00:00:00Z" },
    });

    const user = userEvent.setup();
    render(<ChangeRecordsReview locale="en" labels={LABELS} />);

    const approveButton = await screen.findByRole("button", { name: "Approve" });
    await user.click(approveButton);

    await waitFor(() => {
      expect(approveChangeRecord).toHaveBeenCalledWith("csrf-token", "cr1");
    });
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("shows an entity-unavailable placeholder for a change record whose entity was deleted", async () => {
    getChangeRecords.mockResolvedValue({
      reachable: true,
      data: {
        results: [
          {
            ...PENDING_RECORD,
            entity: {
              title: null,
              route: null,
              verification_status: null,
              source_organization: null,
            },
          },
        ],
        pagination: { page: 1, page_size: 20, total_count: 1 },
      },
    });

    render(<ChangeRecordsReview locale="en" labels={LABELS} />);

    expect(await screen.findByText("This item is no longer available.")).toBeInTheDocument();
  });

  it("shows an empty state when no records match the filter", async () => {
    getChangeRecords.mockResolvedValue({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    render(<ChangeRecordsReview locale="en" labels={LABELS} />);

    expect(await screen.findByText("No change records match this filter.")).toBeInTheDocument();
  });
});
