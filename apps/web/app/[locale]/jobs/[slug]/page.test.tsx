import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { JobDetailApiResult } from "@/lib/jobs";
import messages from "../../../../messages/en.json";

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "Jobs") =>
    createTranslator({ locale: "en", messages, namespace }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const notFound = vi.fn(() => {
  throw new Error("NEXT_NOT_FOUND");
});
vi.mock("next/navigation", () => ({
  notFound: () => notFound(),
}));

const getJobBySlug = vi.fn();
vi.mock("@/lib/jobs", () => ({
  getJobBySlug: (...args: unknown[]) => getJobBySlug(...args),
}));

import JobDetailPage from "./page";

function renderPage(slug: string) {
  return JobDetailPage({ params: Promise.resolve({ locale: "en", slug }) });
}

function resolveJob(result: JobDetailApiResult) {
  getJobBySlug.mockResolvedValue(result);
}

const FIXTURE_JOB = {
  slug: "test-civiclens-job-001",
  title: "Test Civic Clerk Recruitment (Fixture)",
  organization: { name: "Test Recruitment Board — Not Real", org_type: "AUTONOMOUS_BODY" },
  department: { name: "Test Department — Not Real" },
  summary: "A fictional clerk recruitment notice used only to exercise the jobs domain.",
  description: "This is a synthetic fixture — not a real government recruitment notice.",
  employment_type: "PERMANENT" as const,
  category: "clerical",
  state: "Testland",
  district: "Sampleburg",
  min_age: 18,
  max_age: 44,
  qualification_summary: "Bachelor's degree from a recognized university (fictional fixture).",
  experience_summary: null,
  salary_summary: null,
  status: "open",
  verification_status: "VERIFIED" as const,
  last_verified: "2026-08-01T00:00:00Z",
  source: {
    organization: "Test Recruitment Board — Not Real",
    title: "Test Notice — Not Real",
    url: "https://example-test.invalid/notice",
  },
  notifications: [
    {
      notification_number: "TEST_CIVICLENS_JOB_001",
      status: "APPLICATION_OPEN" as const,
      published_date: "2026-07-01",
      application_start: "2026-07-15",
      application_end: "2026-08-15",
      correction_window_end: "2026-08-20",
      exam_date: null,
      total_vacancies: 10,
      official_notification_url: "https://example-test.invalid/notice/test-civiclens-job-001",
      official_application_url: "https://example-test.invalid/apply/test-civiclens-job-001",
      verification_status: "VERIFIED" as const,
      last_verified: "2026-08-01T00:00:00Z",
      source: {
        organization: "Test Recruitment Board — Not Real",
        title: "Test Notice — Not Real",
        url: "https://example-test.invalid/notice",
      },
      vacancies: [
        {
          post_name: "Junior Clerk (Fixture)",
          vacancy_count: 7,
          category: null,
          location: "Sampleburg",
        },
        {
          post_name: "Senior Clerk (Fixture)",
          vacancy_count: 3,
          category: null,
          location: "Sampleburg",
        },
      ],
    },
  ],
};

describe("Job detail page (Phase 6)", () => {
  beforeEach(() => {
    getJobBySlug.mockReset();
    notFound.mockClear();
  });

  it("renders overview, eligibility, and verification for a published job", async () => {
    resolveJob({ reachable: true, data: FIXTURE_JOB });

    const ui = await renderPage("test-civiclens-job-001");
    render(ui);

    expect(
      screen.getByRole("heading", { level: 1, name: "Test Civic Clerk Recruitment (Fixture)" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Test Recruitment Board/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Verified").length).toBeGreaterThan(0);
    expect(screen.getByText("Age: 18–44 years")).toBeInTheDocument();
    expect(
      screen.getByText("Bachelor's degree from a recognized university (fictional fixture)."),
    ).toBeInTheDocument();
  });

  it("renders notification dates, vacancies, and official links", async () => {
    resolveJob({ reachable: true, data: FIXTURE_JOB });

    const ui = await renderPage("test-civiclens-job-001");
    render(ui);

    expect(screen.getByText(/Junior Clerk \(Fixture\)/)).toBeInTheDocument();
    expect(screen.getByText(/Senior Clerk \(Fixture\)/)).toBeInTheDocument();

    const applicationLink = screen.getByRole("link", { name: /official application/i });
    expect(applicationLink).toHaveAttribute(
      "href",
      "https://example-test.invalid/apply/test-civiclens-job-001",
    );
    const notificationLink = screen.getByRole("link", { name: /official notification/i });
    expect(notificationLink).toHaveAttribute(
      "href",
      "https://example-test.invalid/notice/test-civiclens-job-001",
    );
  });

  it("calls notFound() for a job that doesn't exist or isn't published", async () => {
    resolveJob({ reachable: true, data: null });

    await expect(renderPage("does-not-exist")).rejects.toThrow("NEXT_NOT_FOUND");
    expect(notFound).toHaveBeenCalled();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    resolveJob({ reachable: false, error: "API responded with HTTP 500" });

    const ui = await renderPage("test-civiclens-job-001");
    render(ui);

    expect(screen.getByText("API responded with HTTP 500")).toBeInTheDocument();
  });
});
