import { Card } from "../primitives/Card";
import { ExternalLinkIcon } from "../icons";
import { LastVerified } from "./LastVerified";
import { VerificationStatus, type VerificationStatusValue } from "./VerificationStatus";
import styles from "./OfficialSourceCard.module.css";

export interface OfficialSourceCardProps {
  organization: string;
  title: string;
  status: VerificationStatusValue;
  lastVerifiedAt: Date;
  locale: string;
  url: string;
}

/**
 * Purely structural/presentational — no `sources` read API exists yet
 * (Phase 3 built the schema and provenance model, not a public
 * endpoint). Every prop must be supplied by the caller; this component
 * never fetches or fabricates source content itself.
 */
export function OfficialSourceCard({
  organization,
  title,
  status,
  lastVerifiedAt,
  locale,
  url,
}: OfficialSourceCardProps) {
  return (
    <Card className={styles.card}>
      <div className={styles.header}>
        <p className={styles.organization}>{organization}</p>
        <VerificationStatus status={status} />
      </div>
      <h3 className={styles.title}>{title}</h3>
      <div className={styles.footer}>
        <LastVerified date={lastVerifiedAt} locale={locale} />
        <a href={url} target="_blank" rel="noopener noreferrer" className={styles.link}>
          Official source
          <ExternalLinkIcon className={styles.linkIcon} />
        </a>
      </div>
    </Card>
  );
}
