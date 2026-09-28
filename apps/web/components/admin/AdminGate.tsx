"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/components/auth";
import { Spinner } from "@/components/primitives";
import { Link } from "@/i18n/navigation";
import styles from "./AdminGate.module.css";

export interface AdminGateLabels {
  loading: string;
  signInTitle: string;
  signInCta: string;
  notAuthorizedTitle: string;
  notAuthorizedBody: string;
}

const REVIEWER_ROLES = new Set(["editor", "admin"]);

/**
 * The client-side RBAC gate every `/admin/*` page renders behind — a
 * UX convenience only, never the security boundary: the backend's own
 * `require_role` dependency (`app.auth.dependencies`) enforces this
 * independently on every `/api/v1/admin/*` call regardless of what
 * this component renders (this phase's explicit "never trust role
 * information supplied by the client" applies here too — this gate
 * reads `user.role` from the same server-verified session
 * `AuthProvider` already loaded, not from anything client-supplied).
 */
export function AdminGate({ labels, children }: { labels: AdminGateLabels; children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <p className={styles.loading}>
        <Spinner label={labels.loading} />
        <span aria-hidden="true">{labels.loading}</span>
      </p>
    );
  }

  if (!user) {
    return (
      <div className={styles.card}>
        <p className={styles.title}>{labels.signInTitle}</p>
        <Link href="/login" className={styles.link}>
          {labels.signInCta}
        </Link>
      </div>
    );
  }

  if (!REVIEWER_ROLES.has(user.role)) {
    return (
      <div className={styles.card} role="alert">
        <p className={styles.title}>{labels.notAuthorizedTitle}</p>
        <p>{labels.notAuthorizedBody}</p>
      </div>
    );
  }

  return <>{children}</>;
}
