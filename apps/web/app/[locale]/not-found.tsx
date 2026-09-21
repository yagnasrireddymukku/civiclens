import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Container } from "@/components/layout";
import styles from "./boundary.module.css";

export default function NotFound() {
  const t = useTranslations("NotFound");

  return (
    <Container>
      <div className={styles.wrapper}>
        <h1 className={styles.title}>{t("title")}</h1>
        <p>
          <Link href="/" className={styles.link}>
            {t("returnHome")}
          </Link>
        </p>
      </div>
    </Container>
  );
}
