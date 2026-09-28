import { render, screen } from "@testing-library/react";
import { createTranslator } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import messages from "../../../messages/en.json";

vi.mock("next-intl/server", () => ({
  setRequestLocale: vi.fn(),
  getTranslations: async (namespace: "CivicAI") =>
    createTranslator({ locale: "en", messages, namespace }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/ai", () => ({
  askCivicAI: vi.fn(),
}));

import AIPage from "./page";

function renderPage() {
  return AIPage({ params: Promise.resolve({ locale: "en" }) });
}

describe("Civic AI page (Phase 12)", () => {
  it("renders the page title, disclaimer, and question form", async () => {
    const ui = await renderPage();
    render(ui);

    expect(screen.getByRole("heading", { level: 1, name: "Ask CivicLens" })).toBeInTheDocument();
    expect(screen.getByText(/informational only/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Your question")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask" })).toBeInTheDocument();
  });
});
