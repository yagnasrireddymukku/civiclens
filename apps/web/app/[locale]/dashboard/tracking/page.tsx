import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Container } from "@/components/layout";
import type { AppLocale } from "@/i18n/routing";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { TrackingDashboard } from "./TrackingDashboard";
import styles from "./page.module.css";

interface DashboardTrackingPageProps {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: DashboardTrackingPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Dashboard" });
  return {
    ...buildLocaleAwareMetadata({
      locale: locale as AppLocale,
      path: "/dashboard/tracking",
      title: t("title"),
      description: t("metaDescription"),
    }),
    // Personalized, never publicly cached or indexed — docs/FRONTEND.md §3.
    robots: { index: false, follow: false },
  };
}

export default async function DashboardTrackingPage({ params }: DashboardTrackingPageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Dashboard");
  const tt = await getTranslations("Tracking");
  const tn = await getTranslations("Notifications");

  return (
    <Container>
      <div className={styles.page}>
        <h1 className={styles.title}>{t("title")}</h1>
        <TrackingDashboard
          locale={locale}
          labels={{
            loading: t("loading"),
            signInTitle: t("signInTitle"),
            signInBody: t("signInBody"),
            signInCta: t("signInCta"),
            sectionDeadlines: t("sectionDeadlines"),
            noDeadlines: t("noDeadlines"),
            sectionTrackedItems: t("sectionTrackedItems"),
            sectionNotifications: t("sectionNotifications"),
            errorGeneric: t("errorGeneric"),
            trackedEmptyState: tt("emptyState"),
            statusActive: tt("statusActive"),
            statusPaused: tt("statusPaused"),
            pauseAction: tt("pauseAction"),
            resumeAction: tt("resumeAction"),
            removeAction: tt("removeAction"),
            deadlineLabel: tt("deadlineLabel"),
            unavailableNotice: tt("unavailableNotice"),
            notificationsEmptyState: tn("emptyState"),
            markAllRead: tn("markAllRead"),
            markRead: tn("markRead"),
            unreadBadge: tn("unreadBadge"),
            typeDeadlineReminder: tn("typeDeadlineReminder"),
            typeChangeDetected: tn("typeChangeDetected"),
            typeEntityUnavailable: tn("typeEntityUnavailable"),
          }}
        />
      </div>
    </Container>
  );
}
