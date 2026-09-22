import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ServiceListApiResult } from "@/lib/services";
import messages from "../../../messages/en.json";

const push = vi.fn();

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "Services") =>
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

const getServices = vi.fn();
vi.mock("@/lib/services", () => ({
  getServices: (...args: unknown[]) => getServices(...args),
}));

import ServicesPage from "./page";

function renderPage(searchParams: { category?: string; delivery_mode?: string; page?: string }) {
  return ServicesPage({
    params: Promise.resolve({ locale: "en" }),
    searchParams: Promise.resolve(searchParams),
  });
}

function resolveServices(result: ServiceListApiResult) {
  getServices.mockResolvedValue(result);
}

const FIXTURE_SERVICE = {
  slug: "test-civiclens-service-001",
  name: "Test Income Certificate Issuance (Fixture)",
  organization: { name: "Test Recruitment Board — Not Real", org_type: "AUTONOMOUS_BODY" },
  department: { name: "Test Department — Not Real" },
  short_description: "A fictional service used only to exercise the services domain.",
  category: "CERTIFICATES" as const,
  service_type: "certificate issuance",
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

describe("Services list page (Phase 7)", () => {
  beforeEach(() => {
    push.mockClear();
    getServices.mockReset();
  });

  it("always shows the development/test data notice", async () => {
    resolveServices({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    const ui = await renderPage({});
    render(ui);

    expect(
      screen.getByRole("heading", { level: 1, name: "Government Services" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Development data")).toBeInTheDocument();
    expect(screen.getByText(/no real government data yet/i)).toBeInTheDocument();
  });

  it("renders services with their provenance when the API returns results", async () => {
    resolveServices({
      reachable: true,
      data: {
        results: [FIXTURE_SERVICE],
        pagination: { page: 1, page_size: 20, total_count: 1 },
      },
    });

    const ui = await renderPage({});
    render(ui);

    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Test Income Certificate Issuance (Fixture)",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Test Recruitment Board — Not Real")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText(/1 service/i)).toBeInTheDocument();
  });

  it("shows an honest empty state when there are zero matching services", async () => {
    resolveServices({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    const ui = await renderPage({});
    render(ui);

    expect(screen.getByText(/no services match these filters/i)).toBeInTheDocument();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    resolveServices({ reachable: false, error: "API responded with HTTP 500" });

    const ui = await renderPage({});
    render(ui);

    expect(screen.getByRole("alert")).toHaveTextContent("Services unavailable");
    expect(screen.getByRole("alert")).toHaveTextContent("API responded with HTTP 500");
  });

  it("passes the category and delivery_mode filters through to the API call", async () => {
    resolveServices({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    await renderPage({ category: "WELFARE", delivery_mode: "ONLINE" });

    expect(getServices).toHaveBeenCalledWith({
      page: 1,
      category: "WELFARE",
      deliveryMode: "ONLINE",
    });
  });

  it("ignores invalid filter values rather than passing them through", async () => {
    resolveServices({
      reachable: true,
      data: { results: [], pagination: { page: 1, page_size: 20, total_count: 0 } },
    });

    await renderPage({ category: "not-a-real-category" });

    expect(getServices).toHaveBeenCalledWith({
      page: 1,
      category: undefined,
      deliveryMode: undefined,
    });
  });

  it("links to full-text search for free-text queries", async () => {
    resolveServices({
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
