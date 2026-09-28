"use client";

import type {
  AdminEntityType,
  AdminSourceSummary,
  VerificationQueueItem,
  VerificationStatus,
} from "@civiclens/types";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth";
import { Button, Card, Select, Spinner } from "@/components/primitives";
import { Link } from "@/i18n/navigation";
import { getAdminSources, getVerificationQueue, submitVerification } from "@/lib/admin";
import styles from "../page.module.css";

export interface VerificationQueueLabels {
  loading: string;
  errorGeneric: string;
  emptyState: string;
  filterLabel: string;
  filterAll: string;
  entityTypeJob: string;
  entityTypeScheme: string;
  entityTypeService: string;
  entityTypeDocument: string;
  lastVerified: string;
  never: string;
  statusFieldLabel: string;
  sourceFieldLabel: string;
  sourcePlaceholder: string;
  submitAction: string;
  submitSuccess: string;
  statusVerified: string;
  statusNeedsReview: string;
  statusExpired: string;
  statusUnverified: string;
}

const ENTITY_TYPE_LABEL_KEY: Record<AdminEntityType, keyof VerificationQueueLabels> = {
  job: "entityTypeJob",
  scheme: "entityTypeScheme",
  service: "entityTypeService",
  document: "entityTypeDocument",
};

const STATUS_LABEL_KEY: Record<VerificationStatus, keyof VerificationQueueLabels> = {
  VERIFIED: "statusVerified",
  NEEDS_REVIEW: "statusNeedsReview",
  EXPIRED: "statusExpired",
  UNVERIFIED: "statusUnverified",
};

function VerificationForm({
  item,
  sources,
  labels,
  onSubmitted,
}: {
  item: VerificationQueueItem;
  sources: AdminSourceSummary[];
  labels: VerificationQueueLabels;
  onSubmitted: () => void;
}) {
  const { csrfToken } = useAuth();
  const [status, setStatus] = useState<VerificationStatus>("VERIFIED");
  const [sourceId, setSourceId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit() {
    if (!csrfToken || !sourceId) return;
    setSubmitting(true);
    setError(null);
    const result = await submitVerification(
      csrfToken,
      item.entity_type,
      item.entity_id,
      status,
      sourceId,
    );
    setSubmitting(false);
    if (!result.reachable) {
      setError(labels.errorGeneric);
      return;
    }
    setSuccess(true);
    onSubmitted();
  }

  if (success) {
    return (
      <p role="status" className={styles.itemMeta}>
        {labels.submitSuccess}
      </p>
    );
  }

  return (
    <div className={styles.form}>
      <Select
        label={labels.statusFieldLabel}
        value={status}
        onChange={(e) => setStatus(e.target.value as VerificationStatus)}
        options={(Object.keys(STATUS_LABEL_KEY) as VerificationStatus[]).map((value) => ({
          value,
          label: labels[STATUS_LABEL_KEY[value]],
        }))}
      />
      <Select
        label={labels.sourceFieldLabel}
        placeholder={labels.sourcePlaceholder}
        value={sourceId}
        onChange={(e) => setSourceId(e.target.value)}
        options={sources.map((source) => ({
          value: source.id,
          label: `${source.title} — ${source.organization}`,
        }))}
      />
      {error && (
        <p role="alert" className={styles.errorText}>
          {error}
        </p>
      )}
      <Button size="sm" loading={submitting} disabled={!sourceId} onClick={handleSubmit}>
        {labels.submitAction}
      </Button>
    </div>
  );
}

export function VerificationQueue({ labels }: { labels: VerificationQueueLabels }) {
  const [filter, setFilter] = useState<AdminEntityType | "">("");
  const [entries, setEntries] = useState<VerificationQueueItem[] | null>(null);
  const [sources, setSources] = useState<AdminSourceSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    void getAdminSources(1, 50).then((result) => {
      if (result.reachable) setSources(result.data.results);
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    void getVerificationQueue(filter || undefined).then((result) => {
      if (cancelled) return;
      if (result.reachable) {
        setEntries(result.data.results);
      } else {
        setError(labels.errorGeneric);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [filter, reloadKey, labels.errorGeneric]);

  return (
    <div className={styles.sections}>
      <div className={styles.filterRow}>
        <Select
          label={labels.filterLabel}
          value={filter}
          onChange={(e) => setFilter(e.target.value as AdminEntityType | "")}
          options={[
            { value: "", label: labels.filterAll },
            { value: "job", label: labels.entityTypeJob },
            { value: "scheme", label: labels.entityTypeScheme },
            { value: "service", label: labels.entityTypeService },
            { value: "document", label: labels.entityTypeDocument },
          ]}
        />
      </div>

      {error && (
        <p role="alert" className={styles.errorText}>
          {error}
        </p>
      )}

      {entries === null ? (
        <p className={styles.loading}>
          <Spinner label={labels.loading} />
          <span aria-hidden="true">{labels.loading}</span>
        </p>
      ) : entries.length === 0 ? (
        <p className={styles.emptyState}>{labels.emptyState}</p>
      ) : (
        <ul className={styles.list}>
          {entries.map((item) => (
            <li key={`${item.entity_type}-${item.entity_id}`} className={styles.listItem}>
              <Card padded>
                <div className={styles.itemRow}>
                  <Link href={item.route}>{item.title}</Link>
                  <span>{labels[ENTITY_TYPE_LABEL_KEY[item.entity_type]]}</span>
                </div>
                <p className={styles.itemMeta}>
                  {labels.lastVerified}: {item.last_verified ?? labels.never}
                </p>
                <VerificationForm
                  item={item}
                  sources={sources}
                  labels={labels}
                  onSubmitted={() => setReloadKey((k) => k + 1)}
                />
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
