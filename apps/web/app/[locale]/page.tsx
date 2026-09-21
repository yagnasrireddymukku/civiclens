import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { getApiHealth } from "@/lib/api";
import { Container } from "@/components/layout";
import styles from "./page.module.css";

export default async function Home({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);

  const [t, health] = await Promise.all([getTranslations("Home"), getApiHealth()]);

  return (
    <Container>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>{t("heroEyebrow")}</p>
        <h1 className={styles.title}>{t("heroTitle")}</h1>
        <p className={styles.tagline}>{t("heroTagline")}</p>
        <p className={styles.body}>{t("heroBody")}</p>
        <Link href="/dev/design-system" className={styles.showcaseLink}>
          {t("showcaseCta")}
        </Link>
      </section>

      <section aria-label={t("statusHeading")} className={styles.status}>
        <h2 className={styles.statusHeading}>{t("statusHeading")}</h2>
        {health.reachable ? (
          <p>
            {t("statusReachable", {
              status: health.data.status,
              service: health.data.service,
              version: health.data.version,
            })}
          </p>
        ) : (
          <p>{t("statusUnreachable", { error: health.error })}</p>
        )}
      </section>
    </Container>
  );
}
