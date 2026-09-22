import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DocumentListApiResult } from "@/lib/documents";
import messages from "../../../messages/en.json";

const push = vi.fn();

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "Documents") =>
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

const getDocuments = vi.fn();
vi.mock("@/lib/documents", () => ({
  getDocuments: (...args: unknown[]) => getDocuments(...args),
}));

import DocumentsPage from "./page";

function renderPage(searchParams: { document_type?: string; category?: string; page?: string }) {
  return DocumentsPage({
    params: Promise.resolve({ locale: "en" }),
    searchParams: Promise.resolve(searchParams),
  });
}

function resolveDocuments(result: DocumentListApiResult) {
  getDocuments.mockResolvedValue(result);
}

const FIXTURE_DOCUMENT = {
  slug: "test-civiclens-document-002",
  name: "Test Income Certificate (Fixture)",
  organization: { name: "Test Recruitment Board — Not Real", org_type: "AUTONOMOUS_BODY" },
  department: { name: "Test Department — Not Real" },
  short_description: "A fictional document used only to exercise the documents domain.",
  document_type: "CERTIFICATE" as const,
  category: "INCOME" as const,
  delivery_mode: "BOTH" as const,
  state: "Testland",
  district: "Sampleburg",
  status: "available",
  verification_status: "VERIFIED" as const,
  last_verified: "2026-08-01T00:00:00Z",
  source: {
    organization: "Test Recruitment Board — Not Real",
    title: "Test Notice — Not Real",
    url: "https://example-test.invalid/notice",
  },
};

describe("Documents list page (Phase 10)", () => {
  beforeEach(() => {
    push.mockClear();
    getDocuments.mockReset();
  });

  it("always shows the development/test data notice", async () => {
    resolveDocuments({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    const ui = await renderPage({});
    render(ui);

    expect(
      screen.getByRole("heading", { level: 1, name: "Documents & Certificates" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Development data")).toBeInTheDocument();
    expect(screen.getByText(/no real government data yet/i)).toBeInTheDocument();
  });

  it("renders documents with their provenance when the API returns results", async () => {
    resolveDocuments({
      reachable: true,
      data: {
        results: [FIXTURE_DOCUMENT],
        pagination: { page: 1, page_size: 20, total_count: 1 },
      },
    });

    const ui = await renderPage({});
    render(ui);

    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Test Income Certificate (Fixture)",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Test Recruitment Board — Not Real")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText(/1 document/i)).toBeInTheDocument();
  });

  it("shows an honest empty state when there are zero matching documents", async () => {
    resolveDocuments({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    const ui = await renderPage({});
    render(ui);

    expect(screen.getByText(/no documents match these filters/i)).toBeInTheDocument();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    resolveDocuments({ reachable: false, error: "API responded with HTTP 500" });

    const ui = await renderPage({});
    render(ui);

    expect(screen.getByRole("alert")).toHaveTextContent("Documents unavailable");
    expect(screen.getByRole("alert")).toHaveTextContent("API responded with HTTP 500");
  });

  it("passes the document type filter through to the API call", async () => {
    resolveDocuments({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    await renderPage({ document_type: "CERTIFICATE" });

    expect(getDocuments).toHaveBeenCalledWith({
      page: 1,
      documentType: "CERTIFICATE",
      category: undefined,
    });
  });

  it("passes the category filter through to the API call", async () => {
    resolveDocuments({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    await renderPage({ category: "INCOME" });

    expect(getDocuments).toHaveBeenCalledWith({
      page: 1,
      documentType: undefined,
      category: "INCOME",
    });
  });

  it("ignores invalid filter values rather than passing them through", async () => {
    resolveDocuments({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    await renderPage({ document_type: "not-a-real-type", category: "not-a-real-category" });

    expect(getDocuments).toHaveBeenCalledWith({
      page: 1,
      documentType: undefined,
      category: undefined,
    });
  });

  it("links to full-text search for free-text queries", async () => {
    resolveDocuments({
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
