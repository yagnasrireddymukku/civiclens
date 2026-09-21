import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Tabs } from "./Tabs";

const ITEMS = [
  { value: "a", label: "Overview", content: <p>Overview content</p> },
  { value: "b", label: "Documents", content: <p>Documents content</p> },
  { value: "c", label: "History", content: <p>History content</p> },
];

describe("Tabs", () => {
  it("shows only the active panel and marks the active tab selected", () => {
    render(<Tabs label="Example" items={ITEMS} />);

    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Overview content")).toBeVisible();
    expect(screen.getByText("Documents content")).not.toBeVisible();
  });

  it("moves focus and selection with the arrow keys, per the WAI-ARIA tabs pattern", async () => {
    const user = userEvent.setup();
    render(<Tabs label="Example" items={ITEMS} />);

    const overviewTab = screen.getByRole("tab", { name: "Overview" });
    overviewTab.focus();

    await user.keyboard("{ArrowRight}");
    const documentsTab = screen.getByRole("tab", { name: "Documents" });
    expect(documentsTab).toHaveFocus();
    expect(documentsTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Documents content")).toBeVisible();

    await user.keyboard("{ArrowLeft}");
    expect(overviewTab).toHaveFocus();
    expect(overviewTab).toHaveAttribute("aria-selected", "true");
  });

  it("keeps only the active tab in the default tab order (roving tabindex)", () => {
    render(<Tabs label="Example" items={ITEMS} />);

    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("tabIndex", "0");
    expect(screen.getByRole("tab", { name: "Documents" })).toHaveAttribute("tabIndex", "-1");
    expect(screen.getByRole("tab", { name: "History" })).toHaveAttribute("tabIndex", "-1");
  });
});
