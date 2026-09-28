import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const evaluateEligibility = vi.fn();
vi.mock("@/lib/eligibility", () => ({
  evaluateEligibility: (...args: unknown[]) => evaluateEligibility(...args),
}));

import { EligibilityForm } from "./EligibilityForm";

const ATTRIBUTE_LABELS = {
  AGE: "Age",
  INCOME_ANNUAL: "Annual income",
  EDUCATION_LEVEL: "Education level",
  ACADEMIC_PERCENTAGE: "Academic percentage",
  ACADEMIC_CGPA: "Academic CGPA",
  RESIDENCE_STATE: "State of residence",
  CATEGORY: "Category",
} as const;

const EDUCATION_LEVEL_LABELS = {
  SCHOOL: "School",
  INTERMEDIATE: "Intermediate",
  DIPLOMA: "Diploma",
  UNDERGRADUATE: "Undergraduate",
  POSTGRADUATE: "Postgraduate",
  DOCTORAL: "Doctoral",
  PROFESSIONAL: "Professional",
  VOCATIONAL: "Vocational",
  OTHER: "Other",
} as const;

const LABELS = {
  submit: "Check eligibility",
  resultHeading: "Result",
  outcomeEligible: "Eligible",
  outcomeNotEligible: "Not eligible",
  outcomeIncomplete: "Incomplete — more information needed",
  statusPass: "Met",
  statusFail: "Not met",
  statusUnknown: "Unknown — no answer given",
  fieldAge: "Your age (years)",
  fieldIncome: "Your annual household income (₹)",
  fieldEducationLevel: "Your education level",
  fieldPercentage: "Your percentage",
  fieldCgpa: "Your CGPA",
  fieldState: "Your state of residence",
  fieldCategory: "Your category",
  errorGeneric: "Could not check eligibility",
  loading: "Checking…",
};

const AGE_CRITERION = {
  attribute: "AGE" as const,
  operator: "BETWEEN" as const,
  expected: "between 18 and 35 (inclusive)",
  description: "Applicant must be between 18 and 35 years old (fictional fixture).",
};

describe("EligibilityForm (Phase 11)", () => {
  beforeEach(() => {
    evaluateEligibility.mockReset();
  });

  it("renders only the fields the criteria actually ask about", () => {
    render(
      <EligibilityForm
        entityType="JOB"
        entitySlug="test-job"
        criteria={[AGE_CRITERION]}
        attributeLabels={ATTRIBUTE_LABELS}
        educationLevelLabels={EDUCATION_LEVEL_LABELS}
        labels={LABELS}
      />,
    );

    expect(screen.getByLabelText("Your age (years)")).toBeInTheDocument();
    expect(screen.queryByLabelText("Your annual household income (₹)")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Your education level")).not.toBeInTheDocument();
  });

  it("shows ELIGIBLE with per-criterion reasons after a passing submission", async () => {
    evaluateEligibility.mockResolvedValue({
      reachable: true,
      data: {
        entity: { entity_type: "JOB", slug: "test-job", name: "Test Job (Fixture)" },
        supported: true,
        message: null,
        outcome: "ELIGIBLE",
        conditions: [
          {
            attribute: "AGE",
            operator: "BETWEEN",
            description: "Applicant must be between 18 and 35 years old (fictional fixture).",
            expected: "between 18 and 35 (inclusive)",
            submitted_value: "25",
            status: "PASS",
            reason: null,
          },
        ],
        missing_attributes: [],
        failed_attributes: [],
        rule_id: "11111111-1111-1111-1111-111111111111",
        rule_version: 1,
        source: null,
        verification_status: "VERIFIED",
        last_verified: "2026-08-01T00:00:00Z",
        evaluated_at: "2026-09-28T00:00:00Z",
      },
    });

    const user = userEvent.setup();
    render(
      <EligibilityForm
        entityType="JOB"
        entitySlug="test-job"
        criteria={[AGE_CRITERION]}
        attributeLabels={ATTRIBUTE_LABELS}
        educationLevelLabels={EDUCATION_LEVEL_LABELS}
        labels={LABELS}
      />,
    );

    await user.type(screen.getByLabelText("Your age (years)"), "25");
    await user.click(screen.getByRole("button", { name: "Check eligibility" }));

    await waitFor(() => expect(screen.getByText("Eligible")).toBeInTheDocument());
    expect(evaluateEligibility).toHaveBeenCalledWith(
      "JOB",
      "test-job",
      expect.objectContaining({ age: 25 }),
    );
    expect(
      screen.getByText("Applicant must be between 18 and 35 years old (fictional fixture)."),
    ).toBeInTheDocument();
    expect(screen.getByText("Met")).toBeInTheDocument();
  });

  it("shows NOT_ELIGIBLE distinctly from ELIGIBLE, not by color alone", async () => {
    evaluateEligibility.mockResolvedValue({
      reachable: true,
      data: {
        entity: { entity_type: "JOB", slug: "test-job", name: "Test Job (Fixture)" },
        supported: true,
        message: null,
        outcome: "NOT_ELIGIBLE",
        conditions: [
          {
            attribute: "AGE",
            operator: "BETWEEN",
            description: "Applicant must be between 18 and 35 years old (fictional fixture).",
            expected: "between 18 and 35 (inclusive)",
            submitted_value: "90",
            status: "FAIL",
            reason: "The submitted answer does not satisfy this criterion.",
          },
        ],
        missing_attributes: [],
        failed_attributes: ["AGE"],
        rule_id: "11111111-1111-1111-1111-111111111111",
        rule_version: 1,
        source: null,
        verification_status: "VERIFIED",
        last_verified: "2026-08-01T00:00:00Z",
        evaluated_at: "2026-09-28T00:00:00Z",
      },
    });

    const user = userEvent.setup();
    render(
      <EligibilityForm
        entityType="JOB"
        entitySlug="test-job"
        criteria={[AGE_CRITERION]}
        attributeLabels={ATTRIBUTE_LABELS}
        educationLevelLabels={EDUCATION_LEVEL_LABELS}
        labels={LABELS}
      />,
    );

    await user.type(screen.getByLabelText("Your age (years)"), "90");
    await user.click(screen.getByRole("button", { name: "Check eligibility" }));

    await waitFor(() => expect(screen.getByText("Not eligible")).toBeInTheDocument());
    expect(screen.getByText("Not met")).toBeInTheDocument();
  });

  it("shows INCOMPLETE when an answer is left blank", async () => {
    evaluateEligibility.mockResolvedValue({
      reachable: true,
      data: {
        entity: { entity_type: "JOB", slug: "test-job", name: "Test Job (Fixture)" },
        supported: true,
        message: null,
        outcome: "INCOMPLETE",
        conditions: [
          {
            attribute: "AGE",
            operator: "BETWEEN",
            description: "Applicant must be between 18 and 35 years old (fictional fixture).",
            expected: "between 18 and 35 (inclusive)",
            submitted_value: null,
            status: "UNKNOWN",
            reason: "No answer was provided for this attribute.",
          },
        ],
        missing_attributes: ["AGE"],
        failed_attributes: [],
        rule_id: "11111111-1111-1111-1111-111111111111",
        rule_version: 1,
        source: null,
        verification_status: "VERIFIED",
        last_verified: "2026-08-01T00:00:00Z",
        evaluated_at: "2026-09-28T00:00:00Z",
      },
    });

    const user = userEvent.setup();
    render(
      <EligibilityForm
        entityType="JOB"
        entitySlug="test-job"
        criteria={[AGE_CRITERION]}
        attributeLabels={ATTRIBUTE_LABELS}
        educationLevelLabels={EDUCATION_LEVEL_LABELS}
        labels={LABELS}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Check eligibility" }));

    await waitFor(() =>
      expect(screen.getByText("Incomplete — more information needed")).toBeInTheDocument(),
    );
    expect(screen.getByText("Unknown — no answer given")).toBeInTheDocument();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    evaluateEligibility.mockResolvedValue({ reachable: false, error: "Network error" });

    const user = userEvent.setup();
    render(
      <EligibilityForm
        entityType="JOB"
        entitySlug="test-job"
        criteria={[AGE_CRITERION]}
        attributeLabels={ATTRIBUTE_LABELS}
        educationLevelLabels={EDUCATION_LEVEL_LABELS}
        labels={LABELS}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Check eligibility" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByText(/Could not check eligibility/)).toBeInTheDocument();
  });
});
