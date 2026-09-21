import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SearchApiResult } from "@/lib/search";
import messages from "../../../messages/en.json";

const push = vi.fn();

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "Search") =>
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

const getSearchResults = vi.fn();
vi.mock("@/lib/search", () => ({
  getSearchResults: (...args: unknown[]) => getSearchResults(...args),
}));

import SearchPage from "./page";

function renderPage(searchParams: { q?: string; page?: string }) {
  return SearchPage({
    params: Promise.resolve({ locale: "en" }),
    searchParams: Promise.resolve(searchParams),
  });
}

function resolveSearchResults(result: SearchApiResult) {
  getSearchResults.mockResolvedValue(result);
}

const FIXTURE_RESULT = {
  id: "TEST_JOB:1",
  entity_type: "TEST_JOB",
  title: "Test Passport Renewal Notice (Fixture)",
  summary: "A fictional fixture result used only to exercise search.",
  route: "/jobs/test-job-001",
  state: null,
  district: null,
  category: null,
  status: null,
  verification_status: "VERIFIED" as const,
  source: {
    organization: "Test Board — Not Real",
    title: "Test Notice — Not Real",
    url: "https://example-test.invalid/notice",
  },
  last_verified: "2026-08-01T00:00:00Z",
};

describe("Search page (Phase 5)", () => {
  beforeEach(() => {
    push.mockClear();
    getSearchResults.mockReset();
  });

  it("shows a prompt and never calls the API when there's no query", async () => {
    const ui = await renderPage({});
    render(ui);

    expect(screen.getByRole("heading", { level: 1, name: "Search" })).toBeInTheDocument();
    expect(screen.getByText(/enter a search term above/i)).toBeInTheDocument();
    expect(getSearchResults).not.toHaveBeenCalled();
  });

  it("always shows the development/test data notice", async () => {
    const ui = await renderPage({});
    render(ui);

    expect(screen.getByText("Development data")).toBeInTheDocument();
    expect(screen.getByText(/no real government data yet/i)).toBeInTheDocument();
  });

  it("renders results with their provenance when the API returns matches", async () => {
    resolveSearchResults({
      reachable: true,
      data: {
        results: [FIXTURE_RESULT],
        pagination: { page: 1, page_size: 20, total_count: 1 },
        query: { q: "passport", locale: "en", fuzzy_fallback_used: false },
      },
    });

    const ui = await renderPage({ q: "passport" });
    render(ui);

    expect(getSearchResults).toHaveBeenCalledWith({ q: "passport", locale: "en", page: 1 });
    expect(
      screen.getByRole("heading", { level: 3, name: "Test Passport Renewal Notice (Fixture)" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText(/1 result/i)).toBeInTheDocument();
  });

  it("shows an honest empty state when there are zero matches", async () => {
    resolveSearchResults({
      reachable: true,
      data: {
        results: [],
        pagination: { page: 1, page_size: 20, total_count: 0 },
        query: { q: "zzyyxx unrelated", locale: "en", fuzzy_fallback_used: false },
      },
    });

    const ui = await renderPage({ q: "zzyyxx unrelated" });
    render(ui);

    expect(screen.getByText(/no fixtures matched/i)).toBeInTheDocument();
  });

  it("shows a fuzzy-match notice when the API used trigram fallback", async () => {
    resolveSearchResults({
      reachable: true,
      data: {
        results: [{ ...FIXTURE_RESULT, verification_status: "NEEDS_REVIEW" }],
        pagination: { page: 1, page_size: 20, total_count: 1 },
        query: { q: "pasport", locale: "en", fuzzy_fallback_used: true },
      },
    });

    const ui = await renderPage({ q: "pasport" });
    render(ui);

    expect(screen.getByText(/showing similar matches/i)).toBeInTheDocument();
    expect(screen.getByText("Source available")).toBeInTheDocument();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    resolveSearchResults({ reachable: false, error: "API responded with HTTP 500" });

    const ui = await renderPage({ q: "passport" });
    render(ui);

    expect(screen.getByRole("alert")).toHaveTextContent("Search unavailable");
    expect(screen.getByRole("alert")).toHaveTextContent("API responded with HTTP 500");
  });

  it("passes the page query param through to the API call", async () => {
    resolveSearchResults({
      reachable: true,
      data: {
        results: [],
        pagination: { page: 2, page_size: 20, total_count: 0 },
        query: { q: "passport", locale: "en", fuzzy_fallback_used: false },
      },
    });

    await renderPage({ q: "passport", page: "2" });

    expect(getSearchResults).toHaveBeenCalledWith({ q: "passport", locale: "en", page: 2 });
  });
});
