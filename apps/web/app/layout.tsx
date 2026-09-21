import type { ReactNode } from "react";

/**
 * Deliberately does not render <html>/<body> — the locale isn't known
 * at this level yet (docs/FRONTEND.md §7). app/[locale]/layout.tsx
 * renders the actual document shell once the locale segment resolves;
 * this is next-intl's documented App Router pattern for i18n routing.
 */
export default function RootLayout({ children }: { children: ReactNode }) {
  return children;
}
