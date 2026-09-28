import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Container } from "@/components/layout";
import type { AppLocale } from "@/i18n/routing";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { LoginForm } from "./LoginForm";
import styles from "./page.module.css";

interface LoginPageProps {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: LoginPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Auth" });
  return {
    ...buildLocaleAwareMetadata({
      locale: locale as AppLocale,
      path: "/login",
      title: t("loginTitle"),
      description: t("loginDescription"),
    }),
    robots: { index: false, follow: false },
  };
}

export default async function LoginPage({ params }: LoginPageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Auth");

  return (
    <Container>
      <div className={styles.page}>
        <h1 className={styles.title}>{t("loginTitle")}</h1>
        <LoginForm
          labels={{
            email: t("fieldEmail"),
            password: t("fieldPassword"),
            submit: t("loginSubmit"),
            registerPrompt: t("loginRegisterPrompt"),
            registerLink: t("loginRegisterLink"),
          }}
        />
      </div>
    </Container>
  );
}
