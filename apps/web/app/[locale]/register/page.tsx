import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Container } from "@/components/layout";
import type { AppLocale } from "@/i18n/routing";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { RegisterForm } from "./RegisterForm";
import styles from "./page.module.css";

interface RegisterPageProps {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: RegisterPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Auth" });
  return {
    ...buildLocaleAwareMetadata({
      locale: locale as AppLocale,
      path: "/register",
      title: t("registerTitle"),
      description: t("registerDescription"),
    }),
    robots: { index: false, follow: false },
  };
}

export default async function RegisterPage({ params }: RegisterPageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Auth");

  return (
    <Container>
      <div className={styles.page}>
        <h1 className={styles.title}>{t("registerTitle")}</h1>
        <RegisterForm
          labels={{
            email: t("fieldEmail"),
            password: t("fieldPassword"),
            passwordHint: t("fieldPasswordHint"),
            submit: t("registerSubmit"),
            loginPrompt: t("registerLoginPrompt"),
            loginLink: t("registerLoginLink"),
          }}
        />
      </div>
    </Container>
  );
}
