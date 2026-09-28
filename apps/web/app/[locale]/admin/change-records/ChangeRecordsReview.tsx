"use client";

import type { ChangeRecordItem, ChangeReviewStatus } from "@civiclens/types";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth";
import { Button, Card, Select, Spinner } from "@/components/primitives";
import { Link } from "@/i18n/navigation";
import { approveChangeRecord, getChangeRecords, rejectChangeRecord } from "@/lib/admin";
import styles from "../page.module.css";

export interface ChangeRecordsReviewLabels {
  loading: string;
  errorGeneric: string;
  emptyState: string;
  filterLabel: string;
  filterAll: string;
  filterPending: string;
  filterApproved: string;
  filterRejected: string;
  fieldChanged: string;
  detectedOn: string;
  unavailableEntity: string;
  approveAction: string;
  rejectAction: string;
  statusPending: string;
  statusApproved: string;
  statusRejected: string;
}

const STATUS_LABEL_KEY: Record<ChangeReviewStatus, keyof ChangeRecordsReviewLabels> = {
  PENDING: "statusPending",
  APPROVED: "statusApproved",
  REJECTED: "statusRejected",
};

export function ChangeRecordsReview({
  locale,
  labels,
}: {
  locale: string;
  labels: ChangeRecordsReviewLabels;
}) {
  const { csrfToken } = useAuth();
  const [filter, setFilter] = useState<ChangeReviewStatus | "">("PENDING");
  const [records, setRecords] = useState<ChangeRecordItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getChangeRecords(filter || undefined).then((result) => {
      if (cancelled) return;
      if (result.reachable) {
        setRecords(result.data.results);
      } else {
        setError(labels.errorGeneric);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [filter, labels.errorGeneric]);

  async function handleApprove(id: string) {
    if (!csrfToken) return;
    setBusyId(id);
    const result = await approveChangeRecord(csrfToken, id);
    setBusyId(null);
    if (!result.reachable) {
      setError(labels.errorGeneric);
      return;
    }
    setRecords((current) => current?.map((r) => (r.id === id ? result.data : r)) ?? null);
  }

  async function handleReject(id: string) {
    if (!csrfToken) return;
    setBusyId(id);
    const result = await rejectChangeRecord(csrfToken, id);
    setBusyId(null);
    if (!result.reachable) {
      setError(labels.errorGeneric);
      return;
    }
    setRecords((current) => current?.map((r) => (r.id === id ? result.data : r)) ?? null);
  }

  return (
    <div className={styles.sections}>
      <div className={styles.filterRow}>
        <Select
          label={labels.filterLabel}
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value as ChangeReviewStatus | "");
            setRecords(null);
          }}
          options={[
            { value: "", label: labels.filterAll },
            { value: "PENDING", label: labels.filterPending },
            { value: "APPROVED", label: labels.filterApproved },
            { value: "REJECTED", label: labels.filterRejected },
          ]}
        />
      </div>

      {error && (
        <p role="alert" className={styles.errorText}>
          {error}
        </p>
      )}

      {records === null ? (
        <p className={styles.loading}>
          <Spinner label={labels.loading} />
          <span aria-hidden="true">{labels.loading}</span>
        </p>
      ) : records.length === 0 ? (
        <p className={styles.emptyState}>{labels.emptyState}</p>
      ) : (
        <ul className={styles.list}>
          {records.map((record) => (
            <li key={record.id} className={styles.listItem}>
              <Card padded>
                <div className={styles.itemRow}>
                  <span>
                    {record.entity.route ? (
                      <Link href={record.entity.route}>
                        {record.entity.title ?? labels.unavailableEntity}
                      </Link>
                    ) : (
                      (record.entity.title ?? labels.unavailableEntity)
                    )}
                  </span>
                  <span>{labels[STATUS_LABEL_KEY[record.review_status]]}</span>
                </div>
                <p className={styles.itemMeta}>
                  {labels.fieldChanged}: {record.field}
                </p>
                <p className={styles.itemBody}>
                  {record.old_value ?? "—"} → {record.new_value ?? "—"}
                </p>
                <p className={styles.itemMeta}>
                  {labels.detectedOn}:{" "}
                  {new Intl.DateTimeFormat(locale, {
                    dateStyle: "medium",
                    timeStyle: "short",
                  }).format(new Date(record.detected_at))}
                </p>
                {record.review_status === "PENDING" && (
                  <div className={styles.itemActions}>
                    <Button
                      variant="primary"
                      size="sm"
                      loading={busyId === record.id}
                      onClick={() => handleApprove(record.id)}
                    >
                      {labels.approveAction}
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      loading={busyId === record.id}
                      onClick={() => handleReject(record.id)}
                    >
                      {labels.rejectAction}
                    </Button>
                  </div>
                )}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
