import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import messages from "../../messages/en.json";

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: string) => {
    const scoped = (messages as Record<string, Record<string, string>>)[namespace];
    return (key: string, values?: Record<string, string>) => {
      let text = scoped[key];
      if (values) {
        for (const [placeholder, value] of Object.entries(values)) {
          text = text.replace(`{${placeholder}}`, value);
        }
      }
      return text;
    };
  },
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

import Home from "./page";

describe("Home (Phase 4 shell)", () => {
  beforeEach(() => {
    // The API isn't running in this test — asserts the frontend degrades
    // gracefully instead of crashing, per apps/web/lib/api.ts's contract.
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("fetch is not available in tests")));
  });

  it("renders the hero heading and a graceful API-unreachable state", async () => {
    const ui = await Home({ params: Promise.resolve({ locale: "en" }) });
    render(ui);

    expect(
      screen.getByRole("heading", { level: 1, name: /public-information intelligence platform/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/not reachable from this page/i)).toBeInTheDocument();
  });
});
