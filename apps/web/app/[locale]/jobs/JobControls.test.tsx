import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { JobControls } from "./JobControls";

const EMPLOYMENT_TYPE_LABELS = {
  PERMANENT: "Permanent",
  CONTRACT: "Contract",
  TEMPORARY: "Temporary",
} as const;

describe("JobControls (Phase 6)", () => {
  beforeEach(() => {
    push.mockClear();
  });

  it("navigates with the selected employment_type filter", async () => {
    const user = userEvent.setup();
    render(
      <JobControls
        employmentType={undefined}
        employmentTypeLabel="Employment type"
        allLabel="All"
        employmentTypeLabels={EMPLOYMENT_TYPE_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox"), "CONTRACT");

    expect(push).toHaveBeenCalledWith({
      pathname: "/jobs",
      query: { employment_type: "CONTRACT" },
    });
  });

  it("clears the filter when 'All' is selected", async () => {
    const user = userEvent.setup();
    render(
      <JobControls
        employmentType="CONTRACT"
        employmentTypeLabel="Employment type"
        allLabel="All"
        employmentTypeLabels={EMPLOYMENT_TYPE_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox"), "");

    expect(push).toHaveBeenCalledWith({ pathname: "/jobs", query: {} });
  });

  it("preserves the employment_type filter across pagination", async () => {
    const user = userEvent.setup();
    render(
      <JobControls
        employmentType="PERMANENT"
        employmentTypeLabel="Employment type"
        allLabel="All"
        employmentTypeLabels={EMPLOYMENT_TYPE_LABELS}
        page={1}
        totalPages={3}
      />,
    );

    await user.click(screen.getByRole("button", { name: /next page/i }));

    expect(push).toHaveBeenCalledWith({
      pathname: "/jobs",
      query: { employment_type: "PERMANENT", page: "2" },
    });
  });
});
