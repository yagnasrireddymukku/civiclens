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

const EDUCATION_LEVEL_LABELS = {
  SCHOOL: "School",
  INTERMEDIATE: "Intermediate / Higher Secondary",
  DIPLOMA: "Diploma",
  UNDERGRADUATE: "Undergraduate",
  POSTGRADUATE: "Postgraduate",
  DOCTORAL: "Doctoral",
  PROFESSIONAL: "Professional",
  VOCATIONAL: "Vocational",
  OTHER: "Other",
} as const;

describe("SchemeControls (Phase 8/9)", () => {
  beforeEach(() => {
    push.mockClear();
  });

  it("navigates with the selected category filter", async () => {
    const user = userEvent.setup();
    render(
      <SchemeControls
        category={undefined}
        educationLevel={undefined}
        categoryLabel="Category"
        educationLevelLabel="Education level"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        educationLevelLabels={EDUCATION_LEVEL_LABELS}
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

  it("navigates with the selected education level filter", async () => {
    const user = userEvent.setup();
    render(
      <SchemeControls
        category={undefined}
        educationLevel={undefined}
        categoryLabel="Category"
        educationLevelLabel="Education level"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        educationLevelLabels={EDUCATION_LEVEL_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Education level" }),
      "UNDERGRADUATE",
    );

    expect(push).toHaveBeenCalledWith({
      pathname: "/schemes",
      query: { education_level: "UNDERGRADUATE" },
    });
  });

  it("preserves the education level filter when changing category", async () => {
    const user = userEvent.setup();
    render(
      <SchemeControls
        category={undefined}
        educationLevel="UNDERGRADUATE"
        categoryLabel="Category"
        educationLevelLabel="Education level"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        educationLevelLabels={EDUCATION_LEVEL_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Category" }), "SCHOLARSHIP");

    expect(push).toHaveBeenCalledWith({
      pathname: "/schemes",
      query: { category: "SCHOLARSHIP", education_level: "UNDERGRADUATE" },
    });
  });

  it("clears the category filter when 'All' is selected", async () => {
    const user = userEvent.setup();
    render(
      <SchemeControls
        category="PENSION"
        educationLevel={undefined}
        categoryLabel="Category"
        educationLevelLabel="Education level"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        educationLevelLabels={EDUCATION_LEVEL_LABELS}
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

  it("preserves both filters across pagination", async () => {
    const user = userEvent.setup();
    render(
      <SchemeControls
        category="PENSION"
        educationLevel="UNDERGRADUATE"
        categoryLabel="Category"
        educationLevelLabel="Education level"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        educationLevelLabels={EDUCATION_LEVEL_LABELS}
        page={1}
        totalPages={3}
      />,
    );

    await user.click(screen.getByRole("button", { name: /next page/i }));

    expect(push).toHaveBeenCalledWith({
      pathname: "/schemes",
      query: { category: "PENSION", education_level: "UNDERGRADUATE", page: "2" },
    });
  });
});
