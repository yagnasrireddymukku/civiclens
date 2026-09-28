"use client";

import type { AdminSourceSummary, AdminSourceVersionSummary } from "@civiclens/types";
import { useEffect, useState } from "react";
import { Button, Card, Spinner } from "@/components/primitives";
import { getAdminSourceDetail, getAdminSources } from "@/lib/admin";
import styles from "../page.module.css";

export interface AdminSourcesLabels {
  loading: string;
  errorGeneric: string;
  emptyState: string;
  retrievedOn: string;
  versionCount: string;
  viewHistory: string;
  hideHistory: string;
  noVersions: string;
  capturedOn: string;
}

function VersionHistory({
  versions,
  locale,
  labels,
}: {
  versions: AdminSourceVersionSummary[];
  locale: string;
  labels: AdminSourcesLabels;
}) {
  if (versions.length === 0) {
    return <p className={styles.emptyState}>{labels.noVersions}</p>;
  }
  return (
    <ul className={styles.list}>
      {versions.map((version) => (
        <li key={version.id} className={styles.listItem}>
          <p className={styles.itemMeta}>
            {labels.capturedOn}:{" "}
            {new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
              new Date(version.captured_at),
            )}
          </p>
          <p className={styles.itemBody}>{version.content_hash}</p>
        </li>
      ))}
    </ul>
  );
}

export function AdminSources({ locale, labels }: { locale: string; labels: AdminSourcesLabels }) {
  const [sources, setSources] = useState<AdminSourceSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [versions, setVersions] = useState<AdminSourceVersionSummary[] | null>(null);

  useEffect(() => {
    void getAdminSources().then((result) => {
      if (result.reachable) {
        setSources(result.data.results);
      } else {
        setError(labels.errorGeneric);
      }
    });
  }, [labels.errorGeneric]);

  async function toggleHistory(sourceId: string) {
    if (expandedId === sourceId) {
      setExpandedId(null);
      setVersions(null);
      return;
    }
    setExpandedId(sourceId);
    setVersions(null);
    const result = await getAdminSourceDetail(sourceId);
    if (result.reachable) {
      setVersions(result.data.versions);
    } else {
      setError(labels.errorGeneric);
    }
  }

  if (error) {
    return (
      <p role="alert" className={styles.errorText}>
        {error}
      </p>
    );
  }

  if (sources === null) {
    return (
      <p className={styles.loading}>
        <Spinner label={labels.loading} />
        <span aria-hidden="true">{labels.loading}</span>
      </p>
    );
  }

  if (sources.length === 0) {
    return <p className={styles.emptyState}>{labels.emptyState}</p>;
  }

  return (
    <ul className={styles.list}>
      {sources.map((source) => (
        <li key={source.id} className={styles.listItem}>
          <Card padded>
            <div className={styles.itemRow}>
              <a href={source.url} target="_blank" rel="noopener noreferrer">
                {source.title}
              </a>
              <span>{source.organization}</span>
            </div>
            <p className={styles.itemMeta}>
              {labels.retrievedOn}:{" "}
              {new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
                new Date(source.retrieved_date),
              )}{" "}
              · {labels.versionCount}: {source.version_count}
            </p>
            <div className={styles.itemActions}>
              <Button variant="secondary" size="sm" onClick={() => toggleHistory(source.id)}>
                {expandedId === source.id ? labels.hideHistory : labels.viewHistory}
              </Button>
            </div>
            {expandedId === source.id &&
              (versions === null ? (
                <p className={styles.loading}>
                  <Spinner label={labels.loading} />
                  <span aria-hidden="true">{labels.loading}</span>
                </p>
              ) : (
                <VersionHistory versions={versions} locale={locale} labels={labels} />
              ))}
          </Card>
        </li>
      ))}
    </ul>
  );
}
