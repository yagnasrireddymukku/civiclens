import type { ReactNode } from "react";
import { Link } from "@/i18n/navigation";
import { Card } from "../primitives/Card";
import styles from "./InformationCard.module.css";

export interface InformationCardProps {
  /** e.g. "Job", "Scheme", "Service" — the domain, not a real category yet. */
  eyebrow: string;
  title: string;
  description: string;
  /** Small facts shown as a meta row, e.g. state/deadline/organization. */
  meta?: string[];
  badges?: ReactNode;
  href: string;
}

/**
 * The generic card shape future domain listings (jobs, schemes,
 * services, documents, scholarships — docs/ROADMAP.md Phases 6-8) will
 * render real entities into. No domain data exists yet; this is
 * structure only, per this phase's scope.
 */
export function InformationCard({
  eyebrow,
  title,
  description,
  meta,
  badges,
  href,
}: InformationCardProps) {
  return (
    <Card className={styles.card}>
      <p className={styles.eyebrow}>{eyebrow}</p>
      <h3 className={styles.title}>
        <Link href={href} className={styles.titleLink}>
          {title}
        </Link>
      </h3>
      <p className={styles.description}>{description}</p>
      {meta && meta.length > 0 && (
        <ul className={styles.meta}>
          {meta.map((entry) => (
            <li key={entry}>{entry}</li>
          ))}
        </ul>
      )}
      {badges && <div className={styles.badges}>{badges}</div>}
    </Card>
  );
}
