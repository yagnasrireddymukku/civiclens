import { useTranslations } from "next-intl";
import { Container } from "./Container";
import styles from "./Footer.module.css";

const LINKS = ["about", "contact", "privacy", "terms", "disclaimer"] as const;

export function Footer() {
  const t = useTranslations("Footer");

  return (
    <footer className={styles.footer}>
      <Container className={styles.inner}>
        <p className={styles.tagline}>{t("tagline")}</p>
        <nav aria-label="Footer">
          <ul className={styles.links}>
            {LINKS.map((key) => (
              <li key={key}>
                {/* Real static pages (about/contact/privacy/terms/
                    disclaimer) are Phase 6+ content — docs/PRODUCT.md
                    §5 lists them, but none exist yet, so these stay
                    labeled rather than linking to a 404. */}
                <span className={styles.link}>{t(key)}</span>
              </li>
            ))}
          </ul>
        </nav>
      </Container>
    </footer>
  );
}
