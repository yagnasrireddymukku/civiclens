import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminGate, AdminNav } from "@/components/admin";
import { Container } from "@/components/layout";
import type { AppLocale } from "@/i18n/routing";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { AdminSources } from "./AdminSources";
import styles from "../page.module.css";

interface AdminSourcesPageProps {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: AdminSourcesPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Admin" });
  return {
    ...buildLocaleAwareMetadata({
      locale: locale as AppLocale,
      path: "/admin/sources",
      title: t("navSources"),
      description: t("sourcesMetaDescription"),
    }),
    robots: { index: false, follow: false },
  };
}

export default async function AdminSourcesPage({ params }: AdminSourcesPageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Admin");

  return (
    <Container>
      <div className={styles.page}>
        <h1 className={styles.title}>{t("navSources")}</h1>
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
          <AdminSources
            locale={locale}
            labels={{
              loading: t("loading"),
              errorGeneric: t("errorGeneric"),
              emptyState: t("sourcesEmptyState"),
              retrievedOn: t("sourcesRetrievedOn"),
              versionCount: t("sourcesVersionCount"),
              viewHistory: t("sourcesViewHistory"),
              hideHistory: t("sourcesHideHistory"),
              noVersions: t("sourcesNoVersions"),
              capturedOn: t("sourcesCapturedOn"),
            }}
          />
        </AdminGate>
      </div>
    </Container>
  );
}
