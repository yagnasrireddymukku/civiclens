import styles from "./LastVerified.module.css";

export interface LastVerifiedProps {
  date: Date;
  locale: string;
  /** Translated label; defaults to English so the component works
   * standalone (e.g. in tests) without requiring the i18n provider. */
  label?: string;
}

/**
 * The mandatory "Last verified: DATE" display
 * (docs/PRODUCT_REQUIREMENTS.md NFR-T2, docs/SEO.md §10). Date
 * formatting is locale-aware via `Intl.DateTimeFormat`
 * (docs/FRONTEND.md §7), never a hardcoded format string.
 */
export function LastVerified({ date, locale, label = "Last verified" }: LastVerifiedProps) {
  const formatted = new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);

  return (
    <p className={styles.text}>
      <span className={styles.label}>{label}:</span>{" "}
      <time dateTime={date.toISOString().slice(0, 10)}>{formatted}</time>
    </p>
  );
}
