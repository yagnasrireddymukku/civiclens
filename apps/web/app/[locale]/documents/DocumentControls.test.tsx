import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { DocumentControls } from "./DocumentControls";

const DOCUMENT_TYPE_LABELS = {
  CERTIFICATE: "Certificate",
  IDENTITY_DOCUMENT: "Identity Document",
  RECORD: "Record",
  PERMIT: "Permit",
  LICENSE: "License",
  REGISTRATION: "Registration",
  OTHER: "Other",
} as const;

const CATEGORY_LABELS = {
  PERSONAL: "Personal",
  IDENTITY: "Identity",
  RESIDENCE: "Residence",
  INCOME: "Income",
  SOCIAL_CATEGORY: "Social Category",
  EDUCATION: "Education",
  BIRTH_DEATH: "Birth & Death",
  DISABILITY: "Disability",
  LAND_REVENUE: "Land & Revenue",
  EMPLOYMENT: "Employment",
  BUSINESS: "Business",
  FAMILY: "Family",
  OTHER: "Other",
} as const;

describe("DocumentControls (Phase 10)", () => {
  beforeEach(() => {
    push.mockClear();
  });

  it("navigates with the selected document type filter", async () => {
    const user = userEvent.setup();
    render(
      <DocumentControls
        documentType={undefined}
        category={undefined}
        documentTypeLabel="Document type"
        categoryLabel="Category"
        allLabel="All"
        documentTypeLabels={DOCUMENT_TYPE_LABELS}
        categoryLabels={CATEGORY_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Document type" }),
      "CERTIFICATE",
    );

    expect(push).toHaveBeenCalledWith({
      pathname: "/documents",
      query: { document_type: "CERTIFICATE" },
    });
  });

  it("preserves the document type filter when changing category", async () => {
    const user = userEvent.setup();
    render(
      <DocumentControls
        documentType="CERTIFICATE"
        category={undefined}
        documentTypeLabel="Document type"
        categoryLabel="Category"
        allLabel="All"
        documentTypeLabels={DOCUMENT_TYPE_LABELS}
        categoryLabels={CATEGORY_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Category" }), "INCOME");

    expect(push).toHaveBeenCalledWith({
      pathname: "/documents",
      query: { document_type: "CERTIFICATE", category: "INCOME" },
    });
  });

  it("clears the document type filter when 'All' is selected", async () => {
    const user = userEvent.setup();
    render(
      <DocumentControls
        documentType="CERTIFICATE"
        category="INCOME"
        documentTypeLabel="Document type"
        categoryLabel="Category"
        allLabel="All"
        documentTypeLabels={DOCUMENT_TYPE_LABELS}
        categoryLabels={CATEGORY_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Document type" }), "");

    expect(push).toHaveBeenCalledWith({
      pathname: "/documents",
      query: { category: "INCOME" },
    });
  });

  it("preserves both filters across pagination", async () => {
    const user = userEvent.setup();
    render(
      <DocumentControls
        documentType="CERTIFICATE"
        category="INCOME"
        documentTypeLabel="Document type"
        categoryLabel="Category"
        allLabel="All"
        documentTypeLabels={DOCUMENT_TYPE_LABELS}
        categoryLabels={CATEGORY_LABELS}
        page={1}
        totalPages={3}
      />,
    );

    await user.click(screen.getByRole("button", { name: /next page/i }));

    expect(push).toHaveBeenCalledWith({
      pathname: "/documents",
      query: { document_type: "CERTIFICATE", category: "INCOME", page: "2" },
    });
  });
});
