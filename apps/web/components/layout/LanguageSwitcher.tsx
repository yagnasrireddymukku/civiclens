"use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import styles from "./LanguageSwitcher.module.css";

/**
 * Switches locale while staying on the current page — next-intl's
 * `usePathname`/`useRouter` already strip/re-add the locale prefix, so
 * this never needs to parse the URL itself. A native `<select>` keeps
 * it fully keyboard/screen-reader accessible without custom listbox code.
 */
export function LanguageSwitcher() {
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const t = useTranslations("LanguageSwitcher");

  return (
    <label className={styles.wrapper}>
      <span className="visually-hidden">{t("label")}</span>
      <select
        value={locale}
        onChange={(event) => router.replace(pathname, { locale: event.target.value })}
        className={styles.select}
      >
        {routing.locales.map((code) => (
          <option key={code} value={code}>
            {t(code)}
          </option>
        ))}
      </select>
    </label>
  );
}
