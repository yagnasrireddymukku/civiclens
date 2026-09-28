import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminGate, AdminNav } from "@/components/admin";
import { Container } from "@/components/layout";
import type { AppLocale } from "@/i18n/routing";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { ChangeRecordsReview } from "./ChangeRecordsReview";
import styles from "../page.module.css";

interface ChangeRecordsPageProps {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: ChangeRecordsPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Admin" });
  return {
    ...buildLocaleAwareMetadata({
      locale: locale as AppLocale,
      path: "/admin/change-records",
      title: t("navChangeRecords"),
      description: t("changeRecordsMetaDescription"),
    }),
    robots: { index: false, follow: false },
  };
}

export default async function ChangeRecordsPage({ params }: ChangeRecordsPageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Admin");

  return (
    <Container>
      <div className={styles.page}>
        <h1 className={styles.title}>{t("navChangeRecords")}</h1>
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
          <ChangeRecordsReview
            locale={locale}
            labels={{
              loading: t("loading"),
              errorGeneric: t("errorGeneric"),
              emptyState: t("changeRecordsEmptyState"),
              filterLabel: t("changeRecordsFilterLabel"),
              filterAll: t("changeRecordsFilterAll"),
              filterPending: t("statusPending"),
              filterApproved: t("statusApproved"),
              filterRejected: t("statusRejected"),
              fieldChanged: t("changeRecordsFieldChanged"),
              detectedOn: t("changeRecordsDetectedOn"),
              unavailableEntity: t("changeRecordsUnavailableEntity"),
              approveAction: t("changeRecordsApprove"),
              rejectAction: t("changeRecordsReject"),
              statusPending: t("statusPending"),
              statusApproved: t("statusApproved"),
              statusRejected: t("statusRejected"),
            }}
          />
        </AdminGate>
      </div>
    </Container>
  );
}
