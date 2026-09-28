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

const getAdminSources = vi.fn();
const getVerificationQueue = vi.fn();
const submitVerification = vi.fn();
vi.mock("@/lib/admin", () => ({
  getAdminSources: (...args: unknown[]) => getAdminSources(...args),
  getVerificationQueue: (...args: unknown[]) => getVerificationQueue(...args),
  submitVerification: (...args: unknown[]) => submitVerification(...args),
}));

import { VerificationQueue } from "./VerificationQueue";

const LABELS = {
  loading: "Loading…",
  errorGeneric: "Something went wrong. Please try again.",
  emptyState: "Nothing is awaiting verification.",
  filterLabel: "Filter by type",
  filterAll: "All types",
  entityTypeJob: "Job",
  entityTypeScheme: "Scheme",
  entityTypeService: "Service",
  entityTypeDocument: "Document",
  lastVerified: "Last verified",
  never: "Never",
  statusFieldLabel: "Verification decision",
  sourceFieldLabel: "Evidence source",
  sourcePlaceholder: "Select a source",
  submitAction: "Submit verification",
  submitSuccess: "Verification recorded.",
  statusVerified: "Verified",
  statusNeedsReview: "Needs review",
  statusExpired: "Expired",
  statusUnverified: "Unverified",
};

const QUEUE_ITEM = {
  entity_type: "job" as const,
  entity_id: "job1",
  title: "Test Job",
  route: "/jobs/test-job",
  verification_status: "UNVERIFIED" as const,
  last_verified: null,
  source_organization: "Test Board",
};

const SOURCE = {
  id: "source1",
  url: "https://example-test.invalid/notice",
  title: "Test Notice",
  organization: "Test Board",
  source_type: "test-fixture",
  published_date: null,
  retrieved_date: "2026-01-01",
  version_count: 0,
};

describe("VerificationQueue (Admin Intelligence Center)", () => {
  beforeEach(() => {
    getAdminSources.mockReset();
    getVerificationQueue.mockReset();
    submitVerification.mockReset();
    getAdminSources.mockResolvedValue({
      reachable: true,
      data: { results: [SOURCE], pagination: { page: 1, page_size: 50, total_count: 1 } },
    });
  });

  it("shows queue items awaiting verification", async () => {
    getVerificationQueue.mockResolvedValue({
      reachable: true,
      data: { results: [QUEUE_ITEM], pagination: { page: 1, page_size: 20, total_count: 1 } },
    });

    render(<VerificationQueue labels={LABELS} />);

    expect(await screen.findByText("Test Job")).toBeInTheDocument();
    expect(screen.getByText(/Last verified.*Never/)).toBeInTheDocument();
  });

  it("submits a verification decision with the required evidence source", async () => {
    getVerificationQueue.mockResolvedValue({
      reachable: true,
      data: { results: [QUEUE_ITEM], pagination: { page: 1, page_size: 20, total_count: 1 } },
    });
    submitVerification.mockResolvedValue({
      reachable: true,
      data: {
        id: "vr1",
        entity_type: "job",
        entity_id: "job1",
        source_id: "source1",
        status: "VERIFIED",
        verified_by: "u1",
        verified_at: "2026-01-01T00:00:00Z",
        review_due_at: null,
      },
    });

    const user = userEvent.setup();
    render(<VerificationQueue labels={LABELS} />);

    await screen.findByText("Test Job");
    await user.selectOptions(screen.getByLabelText("Evidence source"), "source1");
    await user.click(screen.getByRole("button", { name: "Submit verification" }));

    await waitFor(() => {
      expect(submitVerification).toHaveBeenCalledWith(
        "csrf-token",
        "job",
        "job1",
        "VERIFIED",
        "source1",
      );
    });
    expect(await screen.findByText("Verification recorded.")).toBeInTheDocument();
  });

  it("disables submission until a source is selected", async () => {
    getVerificationQueue.mockResolvedValue({
      reachable: true,
      data: { results: [QUEUE_ITEM], pagination: { page: 1, page_size: 20, total_count: 1 } },
    });

    render(<VerificationQueue labels={LABELS} />);

    await screen.findByText("Test Job");
    expect(screen.getByRole("button", { name: "Submit verification" })).toBeDisabled();
  });

  it("shows an empty state when nothing is awaiting verification", async () => {
    getVerificationQueue.mockResolvedValue({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    render(<VerificationQueue labels={LABELS} />);

    expect(await screen.findByText("Nothing is awaiting verification.")).toBeInTheDocument();
  });
});
