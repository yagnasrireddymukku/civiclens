import { defineRouting } from "next-intl/routing";

/**
 * Launch locales are English and Telugu (docs/PRODUCT.md §5,
 * docs/ARCHITECTURE.md §10). Adding a future locale (Hindi, Tamil,
 * Kannada, Malayalam, Marathi, Bengali, ...) is a configuration/content
 * change — add its code here and a messages/<code>.json catalog, no
 * component code changes required.
 */
export const routing = defineRouting({
  locales: ["en", "te"],
  defaultLocale: "en",
  localePrefix: "always",
});

export type AppLocale = (typeof routing.locales)[number];
