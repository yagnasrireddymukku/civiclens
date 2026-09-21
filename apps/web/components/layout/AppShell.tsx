import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Footer } from "./Footer";
import { TopNav } from "./TopNav";

export function AppShell({ children }: { children: ReactNode }) {
  const t = useTranslations("Shell");

  return (
    <>
      <a href="#main-content" className="skip-link">
        {t("skipToContent")}
      </a>
      <TopNav />
      <main id="main-content">{children}</main>
      <Footer />
    </>
  );
}
