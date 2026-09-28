import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Container } from "@/components/layout";
import type { AppLocale } from "@/i18n/routing";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { ProfilePanel } from "./ProfilePanel";
import styles from "./page.module.css";

interface DashboardProfilePageProps {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: DashboardProfilePageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Profile" });
  return {
    ...buildLocaleAwareMetadata({
      locale: locale as AppLocale,
      path: "/dashboard/profile",
      title: t("title"),
      description: t("metaDescription"),
    }),
    robots: { index: false, follow: false },
  };
}

export default async function DashboardProfilePage({ params }: DashboardProfilePageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Profile");

  return (
    <Container>
      <div className={styles.page}>
        <h1 className={styles.title}>{t("title")}</h1>
        <ProfilePanel
          labels={{
            loading: t("loading"),
            signInTitle: t("signInTitle"),
            signInCta: t("signInCta"),
            emailLabel: t("emailLabel"),
            roleLabel: t("roleLabel"),
            emailNotificationsLabel: t("emailNotificationsLabel"),
            emailNotificationsHint: t("emailNotificationsHint"),
            saveButton: t("saveButton"),
            savedMessage: t("savedMessage"),
            errorGeneric: t("errorGeneric"),
            signOutButton: t("signOutButton"),
          }}
        />
      </div>
    </Container>
  );
}
