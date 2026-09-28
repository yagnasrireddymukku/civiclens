import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ServiceDetailApiResult } from "@/lib/services";
import messages from "../../../../messages/en.json";

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "Services") =>
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

const getServiceBySlug = vi.fn();
vi.mock("@/lib/services", () => ({
  getServiceBySlug: (...args: unknown[]) => getServiceBySlug(...args),
}));

import ServiceDetailPage from "./page";

function renderPage(slug: string) {
  return ServiceDetailPage({ params: Promise.resolve({ locale: "en", slug }) });
}

function resolveService(result: ServiceDetailApiResult) {
  getServiceBySlug.mockResolvedValue(result);
}

const FIXTURE_SERVICE = {
  slug: "test-civiclens-service-001",
  name: "Test Income Certificate Issuance (Fixture)",
  organization: { name: "Test Recruitment Board — Not Real", org_type: "AUTONOMOUS_BODY" },
  department: { name: "Test Department — Not Real" },
  short_description: "A fictional service used only to exercise the services domain.",
  description: "This is a synthetic fixture — not a real government service.",
  category: "CERTIFICATES" as const,
  service_type: "certificate issuance",
  target_audience: "Residents of Testland requiring proof of income (fictional fixture).",
  delivery_mode: "BOTH" as const,
  state: "Testland",
  district: "Sampleburg",
  official_service_url: "https://example-test.invalid/services/test-civiclens-service-001",
  application_url: "https://example-test.invalid/apply/test-civiclens-service-001",
  fee_summary: "Free of cost (fictional fixture).",
  processing_time_summary: "7-10 working days (fictional fixture).",
  location_summary: "Available at Test Mee Seva Center — Not Real, Sampleburg.",
  status: "available",
  verification_status: "VERIFIED" as const,
  last_verified: "2026-08-01T00:00:00Z",
  source: {
    organization: "Test Recruitment Board — Not Real",
    title: "Test Notice — Not Real",
    url: "https://example-test.invalid/notice",
  },
  requirements: [
    {
      requirement_type: "AGE" as const,
      description: "Applicant must be at least 18 years old (fictional fixture).",
      min_value: 18,
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
      channel_type: "ONLINE" as const,
      url: "https://example-test.invalid/apply/test-civiclens-service-001",
      instructions: null,
    },
  ],
};

describe("Service detail page (Phase 7)", () => {
  beforeEach(() => {
    getServiceBySlug.mockReset();
    notFound.mockClear();
  });

  it("renders overview, eligibility, and verification for a published service", async () => {
    resolveService({ reachable: true, data: FIXTURE_SERVICE });

    const ui = await renderPage("test-civiclens-service-001");
    render(ui);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Test Income Certificate Issuance (Fixture)",
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Test Recruitment Board/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Verified").length).toBeGreaterThan(0);
    expect(
      screen.getByText("Applicant must be at least 18 years old (fictional fixture)."),
    ).toBeInTheDocument();
  });

  it("renders required documents, application methods, fees, and processing time", async () => {
    resolveService({ reachable: true, data: FIXTURE_SERVICE });

    const ui = await renderPage("test-civiclens-service-001");
    render(ui);

    expect(screen.getByText(/Aadhaar Card \(Fixture\)/)).toBeInTheDocument();
    expect(screen.getByText("Mandatory")).toBeInTheDocument();
    expect(screen.getByText("Free of cost (fictional fixture).")).toBeInTheDocument();
    expect(screen.getByText("7-10 working days (fictional fixture).")).toBeInTheDocument();

    const links = screen.getAllByRole("link", { name: /official application/i });
    expect(links.some((link) => link.getAttribute("href")?.includes("apply"))).toBe(true);
  });

  it("calls notFound() for a service that doesn't exist or isn't published", async () => {
    resolveService({ reachable: true, data: null });

    await expect(renderPage("does-not-exist")).rejects.toThrow("NEXT_NOT_FOUND");
    expect(notFound).toHaveBeenCalled();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    resolveService({ reachable: false, error: "API responded with HTTP 500" });

    const ui = await renderPage("test-civiclens-service-001");
    render(ui);

    expect(screen.getByText("API responded with HTTP 500")).toBeInTheDocument();
  });
});
