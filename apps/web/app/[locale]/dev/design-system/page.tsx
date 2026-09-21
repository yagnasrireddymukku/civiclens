import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Container } from "@/components/layout";
import { DesignSystemShowcase } from "./Showcase";

export const metadata: Metadata = {
  title: "Design System — CivicLens (internal)",
  robots: { index: false, follow: false },
};

/**
 * Internal, development-only reference for validating the design system
 * (this phase's §22). Never a public CivicLens feature: it 404s outright
 * in production rather than merely being unlinked, so it can't become a
 * public URL by accident.
 */
export default async function DesignSystemPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  // Defense in depth: the primary guard is proxy.ts, which blocks this
  // path at the network layer in production before any rendering starts.
  // This second check covers any request path that somehow bypasses the
  // proxy (e.g. a future rewrite/internal fetch).
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("DesignSystem");

  return (
    <Container>
      <div style={{ paddingBlock: "var(--space-8)" }}>
        <h1 style={{ font: "var(--text-h1)", marginBottom: "var(--space-2)" }}>{t("title")}</h1>
        <p style={{ font: "var(--text-body)", color: "var(--color-text-muted)" }}>
          {t("subtitle")}
        </p>
      </div>
      <DesignSystemShowcase locale={locale} />
    </Container>
  );
}
