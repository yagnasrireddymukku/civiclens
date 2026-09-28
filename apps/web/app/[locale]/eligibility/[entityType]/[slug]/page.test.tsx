import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { EligibilityCriteriaApiResult } from "@/lib/eligibility";
import messages from "../../../../../messages/en.json";

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "Eligibility" | "Schemes") =>
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

const getEligibilityCriteria = vi.fn();
vi.mock("@/lib/eligibility", () => ({
  getEligibilityCriteria: (...args: unknown[]) => getEligibilityCriteria(...args),
  evaluateEligibility: vi.fn(),
}));

import EligibilityPage from "./page";

function renderPage(entityType: string, slug: string) {
  return EligibilityPage({ params: Promise.resolve({ locale: "en", entityType, slug }) });
}

function resolveCriteria(result: EligibilityCriteriaApiResult) {
  getEligibilityCriteria.mockResolvedValue(result);
}

const SUPPORTED_CRITERIA = {
  entity: {
    entity_type: "JOB" as const,
    slug: "test-job",
    name: "Test Junior Assistant (Fixture)",
  },
  supported: true,
  rule_id: "11111111-1111-1111-1111-111111111111",
  rule_version: 1,
  source: {
    organization: "Test Recruitment Board — Not Real",
    title: "Test Notice — Not Real",
    url: "https://example-test.invalid/notice",
  },
  verification_status: "VERIFIED" as const,
  last_verified: "2026-08-01T00:00:00Z",
  criteria: [
    {
      attribute: "AGE" as const,
      operator: "BETWEEN" as const,
      expected: "between 18 and 35 (inclusive)",
      description: "Applicant must be between 18 and 35 years old (fictional fixture).",
    },
  ],
};

describe("Eligibility check page (Phase 11)", () => {
  beforeEach(() => {
    getEligibilityCriteria.mockReset();
    notFound.mockClear();
  });

  it("renders the entity name and published criteria for a supported entity", async () => {
    resolveCriteria({ reachable: true, data: SUPPORTED_CRITERIA });

    const ui = await renderPage("job", "test-job");
    render(ui);

    expect(
      screen.getByRole("heading", { level: 1, name: "Test Junior Assistant (Fixture)" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Applicant must be between 18 and 35 years old (fictional fixture)."),
    ).toBeInTheDocument();
    expect(screen.getByText(/informational check/i)).toBeInTheDocument();
  });

  it("shows the not-supported message and no form when no rule exists", async () => {
    resolveCriteria({
      reachable: true,
      data: {
        ...SUPPORTED_CRITERIA,
        supported: false,
        criteria: [],
        source: null,
        verification_status: null,
        rule_id: null,
        rule_version: null,
      },
    });

    const ui = await renderPage("scheme", "test-scheme");
    render(ui);

    expect(screen.getByText(/No verified eligibility criteria/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Check eligibility" })).not.toBeInTheDocument();
  });

  it("calls notFound() for an unknown entity type segment", async () => {
    await expect(renderPage("not-a-real-type", "test-job")).rejects.toThrow("NEXT_NOT_FOUND");
    expect(notFound).toHaveBeenCalled();
  });

  it("calls notFound() for an entity that doesn't exist or isn't published", async () => {
    resolveCriteria({ reachable: true, data: null });

    await expect(renderPage("job", "does-not-exist")).rejects.toThrow("NEXT_NOT_FOUND");
    expect(notFound).toHaveBeenCalled();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    resolveCriteria({ reachable: false, error: "API responded with HTTP 500" });

    const ui = await renderPage("job", "test-job");
    render(ui);

    expect(screen.getByText("API responded with HTTP 500")).toBeInTheDocument();
  });
});
