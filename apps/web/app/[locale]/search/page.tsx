import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { VerificationStatus } from "@civiclens/types";
import { Alert } from "@/components/feedback";
import { SearchResultCard, type SourceBadgeKind } from "@/components/civic";
import { Container } from "@/components/layout";
import type { AppLocale } from "@/i18n/routing";
import { getSearchResults } from "@/lib/search";
import { buildLocaleAwareMetadata } from "@/lib/seo";
import { SearchControls } from "./SearchControls";
import styles from "./page.module.css";

interface SearchPageProps {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ q?: string; page?: string }>;
}

export async function generateMetadata({ params }: SearchPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Search" });

  return buildLocaleAwareMetadata({
    locale: locale as AppLocale,
    path: "/search",
    title: t("title"),
    description: t("promptBody"),
  });
}

// Only VERIFIED/NEEDS_REVIEW documents are ever indexed
// (apps/api/app/search/service.py's `_INDEXABLE_STATUSES`), but the type
// is the full four-value enum, so this stays total rather than partial.
function toSourceBadgeKind(status: VerificationStatus): SourceBadgeKind {
  return status === "VERIFIED" ? "verified" : "available";
}

// entity_type is a generic, future-module-defined label (this phase
// intentionally creates no real domain tables) — humanized rather than
// mapped through a hardcoded, fixture-specific lookup.
function humanizeEntityType(entityType: string): string {
  return entityType
    .toLowerCase()
    .split("_")
    .filter(Boolean)
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

export default async function SearchPage({ params, searchParams }: SearchPageProps) {
  const { locale } = await params;
  const { q, page: pageParam } = await searchParams;
  setRequestLocale(locale);

  const query = (q ?? "").trim();
  const page = Math.max(1, Number.parseInt(pageParam ?? "1", 10) || 1);

  const [t, result] = await Promise.all([
    getTranslations("Search"),
    query ? getSearchResults({ q: query, locale, page }) : Promise.resolve(null),
  ]);

  const totalPages =
    result?.reachable && result.data.pagination.total_count > 0
      ? Math.ceil(result.data.pagination.total_count / result.data.pagination.page_size)
      : 0;

  const barState = !query ? "idle" : result?.reachable === false ? "error" : "idle";

  return (
    <Container>
      <div className={styles.page}>
        <h1 className={styles.title}>{t("title")}</h1>

        <Alert tone="info" title={t("devDataTitle")}>
          {t("devDataBody")}
        </Alert>

        <SearchControls
          initialQuery={query}
          label={t("searchLabel")}
          placeholder={t("placeholder")}
          state={barState}
          page={page}
          totalPages={totalPages}
        />

        {!query && <p className={styles.prompt}>{t("promptBody")}</p>}

        {query && result?.reachable === false && (
          <Alert tone="error" title={t("errorTitle")}>
            {result.error}
          </Alert>
        )}

        {query && result?.reachable && (
          <>
            <p className={styles.resultsHeading}>
              {t("resultsCount", { count: result.data.pagination.total_count, query })}
            </p>

            {result.data.query.fuzzy_fallback_used && result.data.results.length > 0 && (
              <p className={styles.notice}>{t("fuzzyNotice", { query })}</p>
            )}

            {result.data.results.length === 0 ? (
              <p className={styles.prompt}>{t("noResultsBody", { query })}</p>
            ) : (
              <ul className={styles.results}>
                {result.data.results.map((item) => (
                  <li key={item.id}>
                    <SearchResultCard
                      domain={humanizeEntityType(item.entity_type)}
                      title={item.title}
                      snippet={item.summary ?? ""}
                      sourceKind={toSourceBadgeKind(item.verification_status)}
                      href={item.route}
                    />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </Container>
  );
}
