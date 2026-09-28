import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminGate, AdminNav } from "@/components/admin";
import { Container } from "@/components/layout";
import type { AppLocale } from "@/i18n/routing";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { AdminDashboard } from "./AdminDashboard";
import styles from "./page.module.css";

interface AdminDashboardPageProps {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: AdminDashboardPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Admin" });
  return {
    ...buildLocaleAwareMetadata({
      locale: locale as AppLocale,
      path: "/admin",
      title: t("dashboardTitle"),
      description: t("metaDescription"),
    }),
    robots: { index: false, follow: false },
  };
}

export default async function AdminDashboardPage({ params }: AdminDashboardPageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Admin");

  return (
    <Container>
      <div className={styles.page}>
        <h1 className={styles.title}>{t("dashboardTitle")}</h1>
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
          <AdminDashboard
            labels={{
              loading: t("loading"),
              errorGeneric: t("errorGeneric"),
              sectionPending: t("sectionPending"),
              pendingChangeRecords: t("pendingChangeRecords"),
              sectionDistribution: t("sectionDistribution"),
              sectionRecentChanges: t("sectionRecentChanges"),
              sectionRecentVerifications: t("sectionRecentVerifications"),
              noRecentChanges: t("noRecentChanges"),
              noRecentVerifications: t("noRecentVerifications"),
              statusApproved: t("statusApproved"),
              statusRejected: t("statusRejected"),
              statusPending: t("statusPending"),
            }}
          />
        </AdminGate>
      </div>
    </Container>
  );
}
