import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { SearchControls } from "./SearchControls";

describe("SearchControls (Phase 5)", () => {
  beforeEach(() => {
    push.mockClear();
  });

  it("navigates to a q= URL when a query is submitted", async () => {
    const user = userEvent.setup();
    render(
      <SearchControls
        initialQuery=""
        label="Search CivicLens"
        placeholder="Search…"
        state="idle"
        page={1}
        totalPages={0}
      />,
    );

    await user.type(screen.getByRole("searchbox", { name: "Search CivicLens" }), "passport");
    await user.keyboard("{Enter}");

    expect(push).toHaveBeenCalledWith({ pathname: "/search", query: { q: "passport" } });
  });

  it("navigates back to a bare /search URL when submitted empty", async () => {
    const user = userEvent.setup();
    render(
      <SearchControls
        initialQuery="passport"
        label="Search CivicLens"
        placeholder="Search…"
        state="idle"
        page={1}
        totalPages={0}
      />,
    );

    await user.clear(screen.getByRole("searchbox", { name: "Search CivicLens" }));
    await user.keyboard("{Enter}");

    expect(push).toHaveBeenCalledWith({ pathname: "/search" });
  });

  it("navigates to the next page, preserving the query, on pagination", async () => {
    const user = userEvent.setup();
    render(
      <SearchControls
        initialQuery="passport"
        label="Search CivicLens"
        placeholder="Search…"
        state="idle"
        page={1}
        totalPages={3}
      />,
    );

    await user.click(screen.getByRole("button", { name: /next page/i }));

    expect(push).toHaveBeenCalledWith({
      pathname: "/search",
      query: { q: "passport", page: "2" },
    });
  });
});
