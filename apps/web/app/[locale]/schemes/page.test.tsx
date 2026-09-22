import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SchemeListApiResult } from "@/lib/schemes";
import messages from "../../../messages/en.json";

const push = vi.fn();

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "Schemes") =>
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

const getSchemes = vi.fn();
vi.mock("@/lib/schemes", () => ({
  getSchemes: (...args: unknown[]) => getSchemes(...args),
}));

import SchemesPage from "./page";

function renderPage(searchParams: { category?: string; page?: string }) {
  return SchemesPage({
    params: Promise.resolve({ locale: "en" }),
    searchParams: Promise.resolve(searchParams),
  });
}

function resolveSchemes(result: SchemeListApiResult) {
  getSchemes.mockResolvedValue(result);
}

const FIXTURE_SCHEME = {
  slug: "test-civiclens-scheme-001",
  name: "Test Old-Age Pension Scheme (Fixture)",
  organization: { name: "Test Recruitment Board — Not Real", org_type: "AUTONOMOUS_BODY" },
  department: { name: "Test Department — Not Real" },
  short_description: "A fictional scheme used only to exercise the schemes domain.",
  category: "PENSION" as const,
  state: "Testland",
  district: "Sampleburg",
  status: "active",
  verification_status: "VERIFIED" as const,
  last_verified: "2026-08-01T00:00:00Z",
  source: {
    organization: "Test Recruitment Board — Not Real",
    title: "Test Notice — Not Real",
    url: "https://example-test.invalid/notice",
  },
};

describe("Schemes list page (Phase 8)", () => {
  beforeEach(() => {
    push.mockClear();
    getSchemes.mockReset();
  });

  it("always shows the development/test data notice", async () => {
    resolveSchemes({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    const ui = await renderPage({});
    render(ui);

    expect(
      screen.getByRole("heading", { level: 1, name: "Government Schemes" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Development data")).toBeInTheDocument();
    expect(screen.getByText(/no real government data yet/i)).toBeInTheDocument();
  });

  it("renders schemes with their provenance when the API returns results", async () => {
    resolveSchemes({
      reachable: true,
      data: {
        results: [FIXTURE_SCHEME],
        pagination: { page: 1, page_size: 20, total_count: 1 },
      },
    });

    const ui = await renderPage({});
    render(ui);

    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Test Old-Age Pension Scheme (Fixture)",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Test Recruitment Board — Not Real")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText(/1 scheme/i)).toBeInTheDocument();
  });

  it("shows an honest empty state when there are zero matching schemes", async () => {
    resolveSchemes({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    const ui = await renderPage({});
    render(ui);

    expect(screen.getByText(/no schemes match these filters/i)).toBeInTheDocument();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    resolveSchemes({ reachable: false, error: "API responded with HTTP 500" });

    const ui = await renderPage({});
    render(ui);

    expect(screen.getByRole("alert")).toHaveTextContent("Schemes unavailable");
    expect(screen.getByRole("alert")).toHaveTextContent("API responded with HTTP 500");
  });

  it("passes the category filter through to the API call", async () => {
    resolveSchemes({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    await renderPage({ category: "SCHOLARSHIP" });

    expect(getSchemes).toHaveBeenCalledWith({ page: 1, category: "SCHOLARSHIP" });
  });

  it("ignores invalid filter values rather than passing them through", async () => {
    resolveSchemes({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    await renderPage({ category: "not-a-real-category" });

    expect(getSchemes).toHaveBeenCalledWith({ page: 1, category: undefined });
  });

  it("links to full-text search for free-text queries", async () => {
    resolveSchemes({
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
