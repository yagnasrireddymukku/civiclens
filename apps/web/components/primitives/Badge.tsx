import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Badge.module.css";

export type BadgeTone = "neutral" | "primary" | "success" | "warning" | "error" | "info";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  icon?: ReactNode;
}

/**
 * A generic tone+icon+text badge. Civic-specific badges
 * (components/civic/SourceBadge, VerificationStatus, EligibilityStatus,
 * DeadlineBadge) compose this rather than reimplementing it, and always
 * pass an `icon` alongside `tone` — color alone never carries meaning
 * (docs/FRONTEND.md §6 accessibility rule).
 */
export function Badge({ tone = "neutral", icon, className, children, ...props }: BadgeProps) {
  return (
    <span className={[styles.badge, styles[tone], className].filter(Boolean).join(" ")} {...props}>
      {icon && (
        <span className={styles.icon} aria-hidden="true">
          {icon}
        </span>
      )}
      {children}
    </span>
  );
}
