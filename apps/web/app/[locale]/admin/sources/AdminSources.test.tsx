import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getAdminSources = vi.fn();
const getAdminSourceDetail = vi.fn();
vi.mock("@/lib/admin", () => ({
  getAdminSources: (...args: unknown[]) => getAdminSources(...args),
  getAdminSourceDetail: (...args: unknown[]) => getAdminSourceDetail(...args),
}));

import { AdminSources } from "./AdminSources";

const LABELS = {
  loading: "Loading…",
  errorGeneric: "Something went wrong. Please try again.",
  emptyState: "No sources recorded yet.",
  retrievedOn: "Retrieved on",
  versionCount: "Versions",
  viewHistory: "View history",
  hideHistory: "Hide history",
  noVersions: "No captured versions for this source yet.",
  capturedOn: "Captured on",
};

const SOURCE = {
  id: "source1",
  url: "https://example-test.invalid/notice",
  title: "Test Notice",
  organization: "Test Board",
  source_type: "test-fixture",
  published_date: null,
  retrieved_date: "2026-01-01",
  version_count: 1,
};

describe("AdminSources (Admin Intelligence Center)", () => {
  beforeEach(() => {
    getAdminSources.mockReset();
    getAdminSourceDetail.mockReset();
  });

  it("lists sources with their version counts", async () => {
    getAdminSources.mockResolvedValue({
      reachable: true,
      data: { results: [SOURCE], pagination: { page: 1, page_size: 20, total_count: 1 } },
    });

    render(<AdminSources locale="en" labels={LABELS} />);

    expect(await screen.findByText("Test Notice")).toBeInTheDocument();
    expect(screen.getByText(/Versions.*1/)).toBeInTheDocument();
  });

  it("expands to show version history on request", async () => {
    getAdminSources.mockResolvedValue({
      reachable: true,
      data: { results: [SOURCE], pagination: { page: 1, page_size: 20, total_count: 1 } },
    });
    getAdminSourceDetail.mockResolvedValue({
      reachable: true,
      data: {
        ...SOURCE,
        versions: [
          {
            id: "v1",
            content_hash: "abc123",
            snapshot_ref: null,
            captured_at: "2026-01-01T00:00:00Z",
          },
        ],
      },
    });

    const user = userEvent.setup();
    render(<AdminSources locale="en" labels={LABELS} />);

    await screen.findByText("Test Notice");
    await user.click(screen.getByRole("button", { name: "View history" }));

    await waitFor(() => {
      expect(getAdminSourceDetail).toHaveBeenCalledWith("source1");
    });
    expect(await screen.findByText("abc123")).toBeInTheDocument();
  });

  it("shows a no-versions message for a source with none", async () => {
    getAdminSources.mockResolvedValue({
      reachable: true,
      data: { results: [SOURCE], pagination: { page: 1, page_size: 20, total_count: 1 } },
    });
    getAdminSourceDetail.mockResolvedValue({
      reachable: true,
      data: { ...SOURCE, versions: [] },
    });

    const user = userEvent.setup();
    render(<AdminSources locale="en" labels={LABELS} />);

    await screen.findByText("Test Notice");
    await user.click(screen.getByRole("button", { name: "View history" }));

    expect(
      await screen.findByText("No captured versions for this source yet."),
    ).toBeInTheDocument();
  });

  it("shows an empty state when no sources are recorded", async () => {
    getAdminSources.mockResolvedValue({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    render(<AdminSources locale="en" labels={LABELS} />);

    expect(await screen.findByText("No sources recorded yet.")).toBeInTheDocument();
  });
});
