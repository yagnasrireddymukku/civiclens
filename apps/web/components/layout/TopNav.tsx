"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/components/auth";
import { Link, useRouter } from "@/i18n/navigation";
import { Tooltip } from "../feedback/Tooltip";
import { Container } from "./Container";
import { LanguageSwitcher } from "./LanguageSwitcher";
import styles from "./TopNav.module.css";

/**
 * Every entry below is a real future section (docs/PRODUCT.md §5) that
 * has no route yet (docs/ROADMAP.md Phases 5-11). Per this phase's
 * explicit instruction, these render as clearly-labeled, non-clickable
 * "coming soon" items — not dead links pretending the feature exists.
 */
const COMING_SOON_ITEMS = [
  "jobs",
  "schemes",
  "services",
  "representatives",
  "exams",
  "documents",
  "calculators",
  "ai",
] as const;

export function TopNav() {
  const t = useTranslations();
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, loading, signOut } = useAuth();
  const router = useRouter();

  async function handleSignOut() {
    await signOut();
    router.push("/");
  }

  return (
    <header className={styles.header}>
      <Container className={styles.bar}>
        <Link href="/" className={styles.brand}>
          {t("Shell.brand")}
        </Link>

        <button
          type="button"
          className={styles.menuToggle}
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="visually-hidden">{menuOpen ? "Close menu" : "Open menu"}</span>
          <span aria-hidden="true" className={styles.menuIcon} data-open={menuOpen} />
        </button>

        <nav
          id="primary-navigation"
          aria-label="Primary"
          className={styles.nav}
          data-open={menuOpen}
        >
          <ul className={styles.navList}>
            {COMING_SOON_ITEMS.map((key) => (
              <li key={key}>
                <Tooltip content={t("Nav.comingSoonHint")}>
                  <span className={styles.comingSoon} tabIndex={0}>
                    {t(`Nav.${key}`)}
                    <span className={styles.comingSoonBadge}>{t("Nav.comingSoon")}</span>
                  </span>
                </Tooltip>
              </li>
            ))}
          </ul>
        </nav>

        <div className={styles.actions}>
          <LanguageSwitcher />
          {!loading && user ? (
            <div className={styles.userArea}>
              {(user.role === "editor" || user.role === "admin") && (
                <Link href="/admin" className={styles.userAreaLink}>
                  {t("Shell.adminLink")}
                </Link>
              )}
              <Link href="/dashboard/tracking" className={styles.userAreaLink}>
                {t("Shell.dashboardLink")}
              </Link>
              <button type="button" className={styles.signIn} onClick={handleSignOut}>
                {t("Shell.userAreaSignOut")}
              </button>
            </div>
          ) : !loading ? (
            <Link href="/login" className={styles.signIn}>
              {t("Shell.userAreaSignIn")}
            </Link>
          ) : (
            <span className={styles.signIn} aria-hidden="true" />
          )}
        </div>
      </Container>
    </header>
  );
}
