import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Home from "./page";

describe("Home (Phase 1 placeholder)", () => {
  beforeEach(() => {
    // The API isn't running in this test — asserts the frontend degrades
    // gracefully instead of crashing, per apps/web/lib/api.ts's contract.
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("fetch is not available in tests")));
  });

  it("renders the CivicLens heading and a graceful API-unreachable state", async () => {
    const ui = await Home();
    render(ui);

    expect(screen.getByRole("heading", { level: 1, name: /civiclens/i })).toBeInTheDocument();
    expect(screen.getByText(/not reachable from this page/i)).toBeInTheDocument();
  });
});
