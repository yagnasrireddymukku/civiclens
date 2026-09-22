import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { ServiceControls } from "./ServiceControls";

const CATEGORY_LABELS = {
  CERTIFICATES: "Certificates",
  DOCUMENTS: "Documents",
  WELFARE: "Welfare",
  EDUCATION: "Education",
  HEALTHCARE: "Healthcare",
  AGRICULTURE: "Agriculture",
  EMPLOYMENT: "Employment",
  BUSINESS: "Business",
  TRANSPORT: "Transport",
  MUNICIPAL: "Municipal",
  REVENUE: "Revenue",
  SOCIAL_SECURITY: "Social Security",
  IDENTITY: "Identity",
  UTILITIES: "Utilities",
  OTHER: "Other",
} as const;

const DELIVERY_MODE_LABELS = {
  ONLINE: "Online",
  OFFLINE: "Offline",
  BOTH: "Online & Offline",
} as const;

describe("ServiceControls (Phase 7)", () => {
  beforeEach(() => {
    push.mockClear();
  });

  it("navigates with the selected category filter", async () => {
    const user = userEvent.setup();
    render(
      <ServiceControls
        category={undefined}
        deliveryMode={undefined}
        categoryLabel="Category"
        deliveryModeLabel="Delivery mode"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        deliveryModeLabels={DELIVERY_MODE_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Category" }), "WELFARE");

    expect(push).toHaveBeenCalledWith({
      pathname: "/services",
      query: { category: "WELFARE" },
    });
  });

  it("preserves the category filter when changing delivery mode", async () => {
    const user = userEvent.setup();
    render(
      <ServiceControls
        category="WELFARE"
        deliveryMode={undefined}
        categoryLabel="Category"
        deliveryModeLabel="Delivery mode"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        deliveryModeLabels={DELIVERY_MODE_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Delivery mode" }), "ONLINE");

    expect(push).toHaveBeenCalledWith({
      pathname: "/services",
      query: { category: "WELFARE", delivery_mode: "ONLINE" },
    });
  });

  it("clears the category filter when 'All' is selected", async () => {
    const user = userEvent.setup();
    render(
      <ServiceControls
        category="WELFARE"
        deliveryMode="ONLINE"
        categoryLabel="Category"
        deliveryModeLabel="Delivery mode"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        deliveryModeLabels={DELIVERY_MODE_LABELS}
        page={1}
        totalPages={0}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Category" }), "");

    expect(push).toHaveBeenCalledWith({
      pathname: "/services",
      query: { delivery_mode: "ONLINE" },
    });
  });

  it("preserves both filters across pagination", async () => {
    const user = userEvent.setup();
    render(
      <ServiceControls
        category="WELFARE"
        deliveryMode="ONLINE"
        categoryLabel="Category"
        deliveryModeLabel="Delivery mode"
        allLabel="All"
        categoryLabels={CATEGORY_LABELS}
        deliveryModeLabels={DELIVERY_MODE_LABELS}
        page={1}
        totalPages={3}
      />,
    );

    await user.click(screen.getByRole("button", { name: /next page/i }));

    expect(push).toHaveBeenCalledWith({
      pathname: "/services",
      query: { category: "WELFARE", delivery_mode: "ONLINE", page: "2" },
    });
  });
});
