import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { JobListApiResult } from "@/lib/jobs";
import messages from "../../../messages/en.json";

const push = vi.fn();

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "Jobs") =>
    createTranslator({ locale: "en", messages, namespace }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, ...props }: { href: string; children: ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
  useRouter: () => ({ push }),
}));

const getJobs = vi.fn();
vi.mock("@/lib/jobs", () => ({
  getJobs: (...args: unknown[]) => getJobs(...args),
}));

import JobsPage from "./page";

function renderPage(searchParams: { employment_type?: string; page?: string }) {
  return JobsPage({
    params: Promise.resolve({ locale: "en" }),
    searchParams: Promise.resolve(searchParams),
  });
}

function resolveJobs(result: JobListApiResult) {
  getJobs.mockResolvedValue(result);
}

const FIXTURE_JOB = {
  slug: "test-civiclens-job-001",
  title: "Test Civic Clerk Recruitment (Fixture)",
  organization: { name: "Test Recruitment Board — Not Real", org_type: "AUTONOMOUS_BODY" },
  department: { name: "Test Department — Not Real" },
  summary: "A fictional clerk recruitment notice used only to exercise the jobs domain.",
  employment_type: "PERMANENT" as const,
  category: "clerical",
  state: "Testland",
  district: "Sampleburg",
  status: "open",
  verification_status: "VERIFIED" as const,
  last_verified: "2026-08-01T00:00:00Z",
  source: {
    organization: "Test Recruitment Board — Not Real",
    title: "Test Notice — Not Real",
    url: "https://example-test.invalid/notice",
  },
};

describe("Jobs list page (Phase 6)", () => {
  beforeEach(() => {
    push.mockClear();
    getJobs.mockReset();
  });

  it("always shows the development/test data notice", async () => {
    resolveJobs({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    const ui = await renderPage({});
    render(ui);

    expect(screen.getByRole("heading", { level: 1, name: "Government Jobs" })).toBeInTheDocument();
    expect(screen.getByText("Development data")).toBeInTheDocument();
    expect(screen.getByText(/no real government data yet/i)).toBeInTheDocument();
  });

  it("renders jobs with their provenance when the API returns results", async () => {
    resolveJobs({
      reachable: true,
      data: { results: [FIXTURE_JOB], pagination: { page: 1, page_size: 20, total_count: 1 } },
    });

    const ui = await renderPage({});
    render(ui);

    expect(
      screen.getByRole("heading", { level: 3, name: "Test Civic Clerk Recruitment (Fixture)" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Test Recruitment Board — Not Real")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText(/1 job/i)).toBeInTheDocument();
  });

  it("shows an honest empty state when there are zero matching jobs", async () => {
    resolveJobs({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    const ui = await renderPage({});
    render(ui);

    expect(screen.getByText(/no jobs match these filters/i)).toBeInTheDocument();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    resolveJobs({ reachable: false, error: "API responded with HTTP 500" });

    const ui = await renderPage({});
    render(ui);

    expect(screen.getByRole("alert")).toHaveTextContent("Jobs unavailable");
    expect(screen.getByRole("alert")).toHaveTextContent("API responded with HTTP 500");
  });

  it("passes the employment_type filter through to the API call", async () => {
    resolveJobs({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    await renderPage({ employment_type: "CONTRACT" });

    expect(getJobs).toHaveBeenCalledWith({ page: 1, employmentType: "CONTRACT" });
  });

  it("ignores an invalid employment_type value rather than passing it through", async () => {
    resolveJobs({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    await renderPage({ employment_type: "not-a-real-type" });

    expect(getJobs).toHaveBeenCalledWith({ page: 1, employmentType: undefined });
  });

  it("links to full-text search for free-text queries", async () => {
    resolveJobs({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    const ui = await renderPage({});
    render(ui);

    expect(screen.getByRole("link", { name: /try full-text search/i })).toHaveAttribute(
      "href",
      "/search",
    );
  });
});
