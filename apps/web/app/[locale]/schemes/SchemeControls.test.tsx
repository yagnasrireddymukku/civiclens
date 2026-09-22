import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { SchemeControls } from "./SchemeControls";

const CATEGORY_LABELS = {
  SCHOLARSHIP: "Scholarship",
  PENSION: "Pension",
  SUBSIDY: "Subsidy",
  FINANCIAL_ASSISTANCE: "Financial Assistance",
  INSURANCE: "Insurance",
  HOUSING: "Housing",
  HEALTHCARE: "Healthcare",
  EDUCATION: "Education",
  AGRICULTURE: "Agriculture",
  EMPLOYMENT: "Employment",
  SKILL_DEVELOPMENT: "Skill Development",
  WOMEN_CHILD_WELFARE: "Women & Child Welfare",
  SOCIAL_WELFARE: "Social Welfare",
  BUSINESS_ENTREPRENEURSHIP: "Business & Entrepreneurship",
  DISABILITY_SUPPORT: "Disability Support",
  OTHER: "Other",
} as const;

describe("SchemeControls (Phase 8)", () => {
  beforeEach(() => {
    push.mockClear();
  });

  it("navigates with the selected category filter", async () => {
    const user = userEvent.setup();
    render(
      <SchemeControls
        category={undefined}
        categoryLabel="Category"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Category" }), "PENSION");

    expect(push).toHaveBeenCalledWith({
      pathname: "/schemes",
      query: { category: "PENSION" },
    });
  });

  it("clears the category filter when 'All' is selected", async () => {
    const user = userEvent.setup();
    render(
      <SchemeControls
        category="PENSION"
        categoryLabel="Category"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Category" }), "");

    expect(push).toHaveBeenCalledWith({
      pathname: "/schemes",
      query: {},
    });
  });

  it("preserves the category filter across pagination", async () => {
    const user = userEvent.setup();
    render(
      <SchemeControls
        category="PENSION"
        categoryLabel="Category"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        page={1}
        totalPages={3}
      />,
    );

    await user.click(screen.getByRole("button", { name: /next page/i }));

    expect(push).toHaveBeenCalledWith({
      pathname: "/schemes",
      query: { category: "PENSION", page: "2" },
    });
  });
});
