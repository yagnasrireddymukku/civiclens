import { Link } from "@/i18n/navigation";
import { SourceBadge, type SourceBadgeKind } from "./SourceBadge";
import styles from "./SearchResultCard.module.css";

export interface SearchResultCardProps {
  domain: string;
  title: string;
  snippet: string;
  sourceKind: SourceBadgeKind;
  href: string;
}

/**
 * Reusable visual structure only — docs/SEARCH.md's engine (Postgres
 * FTS + pg_trgm) doesn't exist yet (docs/ROADMAP.md Phase 5). No search
 * request is made from this component.
 */
export function SearchResultCard({
  domain,
  title,
  snippet,
  sourceKind,
  href,
}: SearchResultCardProps) {
  return (
    <article className={styles.result}>
      <p className={styles.domain}>{domain}</p>
      <h3 className={styles.title}>
        <Link href={href}>{title}</Link>
      </h3>
      <p className={styles.snippet}>{snippet}</p>
      <SourceBadge kind={sourceKind} />
    </article>
  );
}
