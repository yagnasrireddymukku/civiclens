import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Container } from "@/components/layout";
import { Breadcrumb } from "@/components/navigation";
import type { AppLocale } from "@/i18n/routing";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { AskCivicAIForm } from "./AskCivicAIForm";
import styles from "./page.module.css";

interface AIPageProps {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: AIPageProps): Promise<Metadata> {
  const { locale } = await params;
  return {
    // This page's answer is per-question and interactive, not stable
    // indexable content — noindex, matching this phase's own SEO note
    // (docs/SEO.md) rather than reusing the indexable-detail-page
    // pattern every browse/detail page above uses.
    ...buildLocaleAwareMetadata({
      locale: locale as AppLocale,
      path: "/ai",
      title: "Ask CivicLens",
      description:
        "Ask a question about published CivicLens jobs, services, schemes, and documents.",
    }),
    robots: { index: false, follow: false },
  };
}

export default async function AIPage({ params }: AIPageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("CivicAI");

  return (
    <Container>
      <div className={styles.page}>
        <Breadcrumb items={[{ label: "CivicLens", href: "/" }, { label: t("pageTitle") }]} />

        <header className={styles.header}>
          <h1 className={styles.title}>{t("pageTitle")}</h1>
          <p className={styles.disclaimer}>{t("disclaimer")}</p>
        </header>

        <AskCivicAIForm
          locale={locale}
          labels={{
            questionLabel: t("questionLabel"),
            questionHint: t("questionHint"),
            submit: t("submitButton"),
            loading: t("loadingLabel"),
            resultHeading: t("sectionAnswer"),
            citationsHeading: t("sectionCitations"),
            needsReviewCaveat: t("needsReviewCaveat"),
            statusInsufficientEvidence: t("statusInsufficientEvidence"),
            statusProviderUnavailable: t("statusProviderUnavailable"),
            statusUngrounded: t("statusUngrounded"),
            searchLinkLabel: t("searchLinkLabel"),
            errorGeneric: t("errorGeneric"),
            lastVerifiedLabel: t("lastVerifiedLabel"),
          }}
        />
      </div>
    </Container>
  );
}
