"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/primitives";
import { Container } from "@/components/layout";
import styles from "./boundary.module.css";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("ErrorBoundary");

  useEffect(() => {
    // Phase 1 has no centralized error tracking yet (see
    // docs/OBSERVABILITY.md); console is the interim foundation.
    console.error(error);
  }, [error]);

  return (
    <Container>
      <div className={styles.wrapper}>
        <h1 className={styles.title}>{t("title")}</h1>
        <p className={styles.description}>{t("description")}</p>
        <Button onClick={() => reset()}>{t("retry")}</Button>
      </div>
    </Container>
  );
}
