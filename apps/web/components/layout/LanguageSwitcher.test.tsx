import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const replace = vi.fn();

vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: () => (key: string) => ({ label: "Language", en: "English", te: "Telugu" })[key],
}));

vi.mock("@/i18n/navigation", () => ({
  usePathname: () => "/dev/design-system",
  useRouter: () => ({ replace }),
}));

vi.mock("@/i18n/routing", () => ({
  routing: { locales: ["en", "te"] },
}));

import { LanguageSwitcher } from "./LanguageSwitcher";

describe("LanguageSwitcher (i18n foundation)", () => {
  it("lists every configured locale as an option", () => {
    render(<LanguageSwitcher />);

    expect(screen.getByRole("option", { name: "English" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Telugu" })).toBeInTheDocument();
  });

  it("switches locale while staying on the current page", async () => {
    const user = userEvent.setup();
    render(<LanguageSwitcher />);

    await user.selectOptions(screen.getByRole("combobox"), "te");

    expect(replace).toHaveBeenCalledWith("/dev/design-system", { locale: "te" });
  });
});
