import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminGate, AdminNav } from "@/components/admin";
import { Container } from "@/components/layout";
import type { AppLocale } from "@/i18n/routing";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { VerificationQueue } from "./VerificationQueue";
import styles from "../page.module.css";

interface VerificationPageProps {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: VerificationPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Admin" });
  return {
    ...buildLocaleAwareMetadata({
      locale: locale as AppLocale,
      path: "/admin/verification",
      title: t("navVerification"),
      description: t("verificationMetaDescription"),
    }),
    robots: { index: false, follow: false },
  };
}

export default async function VerificationPage({ params }: VerificationPageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Admin");

  return (
    <Container>
      <div className={styles.page}>
        <h1 className={styles.title}>{t("navVerification")}</h1>
        <AdminGate
          labels={{
            loading: t("loading"),
            signInTitle: t("signInTitle"),
            signInCta: t("signInCta"),
            notAuthorizedTitle: t("notAuthorizedTitle"),
            notAuthorizedBody: t("notAuthorizedBody"),
          }}
        >
          <AdminNav
            labels={{
              dashboard: t("navDashboard"),
              changeRecords: t("navChangeRecords"),
              verification: t("navVerification"),
              sources: t("navSources"),
            }}
          />
          <VerificationQueue
            labels={{
              loading: t("loading"),
              errorGeneric: t("errorGeneric"),
              emptyState: t("verificationEmptyState"),
              filterLabel: t("verificationFilterLabel"),
              filterAll: t("verificationFilterAll"),
              entityTypeJob: t("entityTypeJob"),
              entityTypeScheme: t("entityTypeScheme"),
              entityTypeService: t("entityTypeService"),
              entityTypeDocument: t("entityTypeDocument"),
              lastVerified: t("verificationLastVerified"),
              never: t("verificationNever"),
              statusFieldLabel: t("verificationStatusFieldLabel"),
              sourceFieldLabel: t("verificationSourceFieldLabel"),
              sourcePlaceholder: t("verificationSourcePlaceholder"),
              submitAction: t("verificationSubmitAction"),
              submitSuccess: t("verificationSubmitSuccess"),
              statusVerified: t("statusVerified"),
              statusNeedsReview: t("statusNeedsReview"),
              statusExpired: t("statusExpired"),
              statusUnverified: t("statusUnverified"),
            }}
          />
        </AdminGate>
      </div>
    </Container>
  );
}
