"use client";

import type {
  RecentChangeDecision,
  RecentVerification,
  VerificationStatus,
} from "@civiclens/types";
import { useEffect, useState } from "react";
import { VerificationStatus as VerificationStatusBadge } from "@/components/civic";
import { Card, Spinner } from "@/components/primitives";
import { getAdminDashboard } from "@/lib/admin";
import styles from "./page.module.css";

export interface AdminDashboardLabels {
  loading: string;
  errorGeneric: string;
  sectionPending: string;
  pendingChangeRecords: string;
  sectionDistribution: string;
  sectionRecentChanges: string;
  sectionRecentVerifications: string;
  noRecentChanges: string;
  noRecentVerifications: string;
  statusApproved: string;
  statusRejected: string;
  statusPending: string;
}

const STATUS_ORDER: VerificationStatus[] = ["VERIFIED", "NEEDS_REVIEW", "UNVERIFIED", "EXPIRED"];

function decisionLabel(decision: RecentChangeDecision, labels: AdminDashboardLabels): string {
  if (decision.review_status === "APPROVED") return labels.statusApproved;
  if (decision.review_status === "REJECTED") return labels.statusRejected;
  return labels.statusPending;
}

export function AdminDashboard({ labels }: { labels: AdminDashboardLabels }) {
  const [pendingChangeRecords, setPendingChangeRecords] = useState<number | null>(null);
  const [statusCounts, setStatusCounts] = useState<Partial<
    Record<VerificationStatus, number>
  > | null>(null);
  const [recentChanges, setRecentChanges] = useState<RecentChangeDecision[] | null>(null);
  const [recentVerifications, setRecentVerifications] = useState<RecentVerification[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getAdminDashboard().then((result) => {
      if (cancelled) return;
      if (result.reachable) {
        setPendingChangeRecords(result.data.pending_change_records);
        setStatusCounts(result.data.verification_status_counts);
        setRecentChanges(result.data.recent_change_decisions);
        setRecentVerifications(result.data.recent_verifications);
      } else {
        setError(labels.errorGeneric);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [labels.errorGeneric]);

  if (error) {
    return (
      <p role="alert" className={styles.errorText}>
        {error}
      </p>
    );
  }

  if (
    pendingChangeRecords === null ||
    statusCounts === null ||
    recentChanges === null ||
    recentVerifications === null
  ) {
    return (
      <p className={styles.loading}>
        <Spinner label={labels.loading} />
        <span aria-hidden="true">{labels.loading}</span>
      </p>
    );
  }

  return (
    <div className={styles.sections}>
      <section aria-labelledby="pending-heading" className={styles.section}>
        <h2 id="pending-heading" className={styles.sectionHeading}>
          {labels.sectionPending}
        </h2>
        <Card padded className={styles.metricCard}>
          <p className={styles.metricValue}>{pendingChangeRecords}</p>
          <p className={styles.metricLabel}>{labels.pendingChangeRecords}</p>
        </Card>
      </section>

      <section aria-labelledby="distribution-heading" className={styles.section}>
        <h2 id="distribution-heading" className={styles.sectionHeading}>
          {labels.sectionDistribution}
        </h2>
        <ul className={styles.distributionList}>
          {STATUS_ORDER.map((status) => (
            <li key={status} className={styles.distributionItem}>
              <VerificationStatusBadge status={status} />
              <span className={styles.distributionCount}>{statusCounts[status] ?? 0}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="recent-changes-heading" className={styles.section}>
        <h2 id="recent-changes-heading" className={styles.sectionHeading}>
          {labels.sectionRecentChanges}
        </h2>
        {recentChanges.length === 0 ? (
          <p className={styles.emptyState}>{labels.noRecentChanges}</p>
        ) : (
          <ul className={styles.list}>
            {recentChanges.map((decision) => (
              <li key={decision.id} className={styles.listItem}>
                <Card padded>
                  <p className={styles.itemMeta}>
                    {decision.entity_type} · {decision.field}
                  </p>
                  <p>{decisionLabel(decision, labels)}</p>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="recent-verifications-heading" className={styles.section}>
        <h2 id="recent-verifications-heading" className={styles.sectionHeading}>
          {labels.sectionRecentVerifications}
        </h2>
        {recentVerifications.length === 0 ? (
          <p className={styles.emptyState}>{labels.noRecentVerifications}</p>
        ) : (
          <ul className={styles.list}>
            {recentVerifications.map((verification) => (
              <li key={verification.id} className={styles.listItem}>
                <Card padded>
                  <p className={styles.itemMeta}>{verification.entity_type}</p>
                  <VerificationStatusBadge status={verification.status} />
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
