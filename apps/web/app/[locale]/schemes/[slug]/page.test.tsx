import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SchemeDetailApiResult } from "@/lib/schemes";
import messages from "../../../../messages/en.json";

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "Schemes") =>
    createTranslator({ locale: "en", messages, namespace }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

// Tracking controls are a separate concern with their own dedicated
// test coverage (components/tracking/TrackButton.test.tsx) — stubbed
// here so this domain page's tests don't need auth/i18n client context.
vi.mock("@/components/tracking", () => ({
  TrackButton: () => null,
}));

const notFound = vi.fn(() => {
  throw new Error("NEXT_NOT_FOUND");
});
vi.mock("next/navigation", () => ({
  notFound: () => notFound(),
}));

const getSchemeBySlug = vi.fn();
vi.mock("@/lib/schemes", () => ({
  getSchemeBySlug: (...args: unknown[]) => getSchemeBySlug(...args),
}));

import SchemeDetailPage from "./page";

function renderPage(slug: string) {
  return SchemeDetailPage({ params: Promise.resolve({ locale: "en", slug }) });
}

function resolveScheme(result: SchemeDetailApiResult) {
  getSchemeBySlug.mockResolvedValue(result);
}

const FIXTURE_SCHEME = {
  slug: "test-civiclens-scheme-001",
  name: "Test Old-Age Pension Scheme (Fixture)",
  organization: { name: "Test Recruitment Board — Not Real", org_type: "AUTONOMOUS_BODY" },
  department: { name: "Test Department — Not Real" },
  short_description: "A fictional scheme used only to exercise the schemes domain.",
  description: "This is a synthetic fixture — not a real government scheme.",
  category: "PENSION" as const,
  target_audience: "Residents of Testland aged 60 and above (fictional fixture).",
  state: "Testland",
  district: "Sampleburg",
  official_scheme_url: "https://example-test.invalid/schemes/test-civiclens-scheme-001",
  application_url: "https://example-test.invalid/apply/test-civiclens-scheme-001",
  status: "active",
  verification_status: "VERIFIED" as const,
  last_verified: "2026-08-01T00:00:00Z",
  source: {
    organization: "Test Recruitment Board — Not Real",
    title: "Test Notice — Not Real",
    url: "https://example-test.invalid/notice",
  },
  benefits: [
    {
      benefit_type: "CASH_TRANSFER" as const,
      description: "Monthly pension amount (fictional fixture — no real figure implied).",
      amount_summary: "Fictional fixture amount — not a real figure.",
      frequency_summary: "Monthly",
    },
  ],
  requirements: [
    {
      requirement_type: "AGE" as const,
      description: "Applicant must be at least 60 years old (fictional fixture).",
      min_value: 60,
      max_value: null,
    },
  ],
  required_documents: [
    {
      name: "Aadhaar Card (Fixture)",
      description: "Proof of identity — fictional fixture, not a real requirement.",
      is_mandatory: true,
    },
  ],
  application_methods: [
    {
      channel_type: "SERVICE_CENTER" as const,
      url: null,
      instructions: "Visit any Test Mee Seva Center — Not Real with required documents.",
    },
  ],
  related_services: [
    {
      slug: "test-civiclens-linked-service-001",
      name: "Test Income Certificate Issuance for Scheme Linking (Fixture)",
      note: "Applicants typically obtain this service's income certificate first (fictional fixture).",
    },
  ],
  scholarship: null,
};

const FIXTURE_SCHOLARSHIP_SCHEME = {
  ...FIXTURE_SCHEME,
  slug: "test-civiclens-scheme-002",
  name: "Test Merit Scholarship Scheme (Fixture)",
  category: "SCHOLARSHIP" as const,
  related_services: [],
  scholarship: {
    education_level: "UNDERGRADUATE" as const,
    course_discipline: "Any UGC-recognized undergraduate discipline (fictional fixture).",
    institution_type: "Government or government-aided colleges (fictional fixture).",
    study_mode: "FULL_TIME" as const,
    year_of_study: "Any year of study (fictional fixture).",
    // A string, not a number — Pydantic v2 serializes the backend's
    // `Decimal` field this way (verified against a real response; see
    // packages/types's matching comment).
    minimum_percentage: "60.00",
    minimum_cgpa: null,
    academic_requirement_notes:
      "Must not hold another active scholarship for the same academic year (fictional fixture).",
    application_opens: "2026-06-01",
    application_closes: "2026-07-31",
    correction_window_end: "2026-08-07",
    academic_year: "2026-27",
    renewable: true,
    renewal_notes:
      "Renewable each academic year subject to continued enrollment and minimum percentage (fictional fixture).",
  },
};

describe("Scheme detail page (Phase 8)", () => {
  beforeEach(() => {
    getSchemeBySlug.mockReset();
    notFound.mockClear();
  });

  it("renders overview, benefits, eligibility, and verification for a published scheme", async () => {
    resolveScheme({ reachable: true, data: FIXTURE_SCHEME });

    const ui = await renderPage("test-civiclens-scheme-001");
    render(ui);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Test Old-Age Pension Scheme (Fixture)",
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Test Recruitment Board/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Verified").length).toBeGreaterThan(0);
    expect(screen.getByText(/Monthly pension amount \(fictional fixture/)).toBeInTheDocument();
    expect(
      screen.getByText("Applicant must be at least 60 years old (fictional fixture)."),
    ).toBeInTheDocument();
  });

  it("renders required documents, application methods, and related services", async () => {
    resolveScheme({ reachable: true, data: FIXTURE_SCHEME });

    const ui = await renderPage("test-civiclens-scheme-001");
    render(ui);

    expect(screen.getByText(/Aadhaar Card \(Fixture\)/)).toBeInTheDocument();
    expect(screen.getByText("Mandatory")).toBeInTheDocument();
    expect(screen.getByText(/Visit any Test Mee Seva Center — Not Real/)).toBeInTheDocument();
    expect(
      screen.getByText(/Test Income Certificate Issuance for Scheme Linking/),
    ).toBeInTheDocument();
  });

  it("calls notFound() for a scheme that doesn't exist or isn't published", async () => {
    resolveScheme({ reachable: true, data: null });

    await expect(renderPage("does-not-exist")).rejects.toThrow("NEXT_NOT_FOUND");
    expect(notFound).toHaveBeenCalled();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    resolveScheme({ reachable: false, error: "API responded with HTTP 500" });

    const ui = await renderPage("test-civiclens-scheme-001");
    render(ui);

    expect(screen.getByText("API responded with HTTP 500")).toBeInTheDocument();
  });

  it("does not render a scholarship details section for a non-scholarship scheme", async () => {
    resolveScheme({ reachable: true, data: FIXTURE_SCHEME });

    const ui = await renderPage("test-civiclens-scheme-001");
    render(ui);

    expect(screen.queryByText("Scholarship details")).not.toBeInTheDocument();
  });
});

describe("Scheme detail page — scholarship details (Phase 9)", () => {
  beforeEach(() => {
    getSchemeBySlug.mockReset();
    notFound.mockClear();
  });

  it("renders education level, academic requirements, and application window", async () => {
    resolveScheme({ reachable: true, data: FIXTURE_SCHOLARSHIP_SCHEME });

    const ui = await renderPage("test-civiclens-scheme-002");
    render(ui);

    expect(screen.getByText("Scholarship details")).toBeInTheDocument();
    expect(screen.getByText(/Education level: Undergraduate/)).toBeInTheDocument();
    expect(screen.getByText(/Minimum percentage required: 60\.00%/)).toBeInTheDocument();
    expect(screen.getByText(/Renewable: Yes/)).toBeInTheDocument();
    expect(screen.getByText(/Application opens:/)).toBeInTheDocument();
    expect(screen.getByText(/Application closes:/)).toBeInTheDocument();
  });

  it("never renders a personalized eligibility verdict", async () => {
    // The page legitimately shows an "Eligibility information" section
    // (documented, source-backed requirements) — what it must never show
    // is a computed ELIGIBLE/NOT_ELIGIBLE/INCOMPLETE verdict for this
    // particular visitor (this phase's §11/§29; Phase 10's domain).
    resolveScheme({ reachable: true, data: FIXTURE_SCHOLARSHIP_SCHEME });

    const ui = await renderPage("test-civiclens-scheme-002");
    render(ui);

    expect(screen.queryByText(/^ELIGIBLE$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^NOT_ELIGIBLE$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^INCOMPLETE$/)).not.toBeInTheDocument();
  });
});
