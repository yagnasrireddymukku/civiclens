import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DocumentDetailApiResult } from "@/lib/documents";
import messages from "../../../../messages/en.json";

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "Documents") =>
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

const getDocumentBySlug = vi.fn();
vi.mock("@/lib/documents", () => ({
  getDocumentBySlug: (...args: unknown[]) => getDocumentBySlug(...args),
}));

import DocumentDetailPage from "./page";

function renderPage(slug: string) {
  return DocumentDetailPage({ params: Promise.resolve({ locale: "en", slug }) });
}

function resolveDocument(result: DocumentDetailApiResult) {
  getDocumentBySlug.mockResolvedValue(result);
}

const FIXTURE_DOCUMENT = {
  slug: "test-civiclens-document-002",
  name: "Test Income Certificate (Fixture)",
  organization: { name: "Test Recruitment Board — Not Real", org_type: "AUTONOMOUS_BODY" },
  department: { name: "Test Department — Not Real" },
  short_description: "A fictional document used only to exercise the documents domain.",
  description: "This is a synthetic fixture — not a real government certificate.",
  document_type: "CERTIFICATE" as const,
  category: "INCOME" as const,
  purpose: "Used to establish officially recognized income status (fictional fixture).",
  delivery_mode: "BOTH" as const,
  state: "Testland",
  district: "Sampleburg",
  official_document_url: "https://example-test.invalid/documents/test-civiclens-document-002",
  application_url: "https://example-test.invalid/apply/test-civiclens-document-002",
  fee_summary: "Free of cost (fictional fixture).",
  processing_time_summary: "7-10 working days (fictional fixture).",
  validity_summary: "Valid for 6 months from the date of issue (fictional fixture).",
  renewal_summary: "Reapply after expiry — no separate renewal process (fictional fixture).",
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
      requirement_type: "RESIDENCY" as const,
      description: "Applicant must be a resident of Testland (fictional fixture).",
      min_value: null,
      max_value: null,
    },
  ],
  supporting_documents: [
    {
      name: "Aadhaar Card (Fixture)",
      description: "Proof of identity — fictional fixture, not a real requirement.",
      is_mandatory: true,
      civic_document: null,
    },
    {
      name: "Residence Certificate (Fixture)",
      description: "Proof of residence — fictional fixture, not a real requirement.",
      is_mandatory: true,
      civic_document: {
        slug: "test-civiclens-document-001",
        name: "Test Residence Certificate (Fixture)",
      },
    },
  ],
  application_methods: [
    {
      channel_type: "ONLINE" as const,
      url: "https://example-test.invalid/apply/test-civiclens-document-002",
      instructions: null,
    },
  ],
  service: {
    slug: "test-civiclens-linked-service-002",
    name: "Test Income Certificate Issuance Service (Fixture)",
  },
  required_by: [
    {
      entity_type: "scheme" as const,
      slug: "test-civiclens-scheme-004",
      name: "Test Family Welfare Assistance Scheme (Fixture)",
    },
  ],
};

describe("Document detail page (Phase 10)", () => {
  beforeEach(() => {
    getDocumentBySlug.mockReset();
    notFound.mockClear();
  });

  it("renders overview, purpose, requirements, and verification for a published document", async () => {
    resolveDocument({ reachable: true, data: FIXTURE_DOCUMENT });

    const ui = await renderPage("test-civiclens-document-002");
    render(ui);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Test Income Certificate (Fixture)",
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Test Recruitment Board/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Verified").length).toBeGreaterThan(0);
    expect(
      screen.getByText(
        "Used to establish officially recognized income status (fictional fixture).",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Applicant must be a resident of Testland (fictional fixture)."),
    ).toBeInTheDocument();
  });

  it("renders supporting documents, linking to a modeled CivicDocument when one exists", async () => {
    resolveDocument({ reachable: true, data: FIXTURE_DOCUMENT });

    const ui = await renderPage("test-civiclens-document-002");
    render(ui);

    expect(screen.getByText(/Aadhaar Card \(Fixture\)/)).toBeInTheDocument();
    expect(screen.getAllByText("Mandatory").length).toBeGreaterThan(0);

    const residenceLink = screen.getByRole("link", { name: "Residence Certificate (Fixture)" });
    expect(residenceLink).toHaveAttribute("href", "/documents/test-civiclens-document-001");
  });

  it("renders application methods, fees, processing time, and validity", async () => {
    resolveDocument({ reachable: true, data: FIXTURE_DOCUMENT });

    const ui = await renderPage("test-civiclens-document-002");
    render(ui);

    expect(screen.getByText(/Free of cost \(fictional fixture\)/)).toBeInTheDocument();
    expect(screen.getByText(/7-10 working days \(fictional fixture\)/)).toBeInTheDocument();
    expect(
      screen.getByText("Valid for 6 months from the date of issue (fictional fixture)."),
    ).toBeInTheDocument();

    const links = screen.getAllByRole("link", { name: /official application/i });
    expect(links.some((link) => link.getAttribute("href")?.includes("apply"))).toBe(true);
  });

  it("renders the related government service and the required-by section", async () => {
    resolveDocument({ reachable: true, data: FIXTURE_DOCUMENT });

    const ui = await renderPage("test-civiclens-document-002");
    render(ui);

    expect(
      screen.getByText("Test Income Certificate Issuance Service (Fixture)"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Test Family Welfare Assistance Scheme \(Fixture\) \(Scheme\)/),
    ).toBeInTheDocument();
  });

  it("calls notFound() for a document that doesn't exist or isn't published", async () => {
    resolveDocument({ reachable: true, data: null });

    await expect(renderPage("does-not-exist")).rejects.toThrow("NEXT_NOT_FOUND");
    expect(notFound).toHaveBeenCalled();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    resolveDocument({ reachable: false, error: "API responded with HTTP 500" });

    const ui = await renderPage("test-civiclens-document-002");
    render(ui);

    expect(screen.getByText("API responded with HTTP 500")).toBeInTheDocument();
  });

  it("does not render a related-service section when there is none", async () => {
    resolveDocument({
      reachable: true,
      data: { ...FIXTURE_DOCUMENT, service: null, required_by: [] },
    });

    const ui = await renderPage("test-civiclens-document-002");
    render(ui);

    expect(screen.queryByText("Related government service")).not.toBeInTheDocument();
    expect(screen.queryByText("Where this document may be required")).not.toBeInTheDocument();
  });
});
