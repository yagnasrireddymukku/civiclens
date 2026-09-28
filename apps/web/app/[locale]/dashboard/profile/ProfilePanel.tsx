"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth";
import { Button, Card, Spinner, Switch } from "@/components/primitives";
import { Link, useRouter } from "@/i18n/navigation";
import { updateNotificationPreference } from "@/lib/auth";
import styles from "./page.module.css";

export interface ProfileLabels {
  loading: string;
  signInTitle: string;
  signInCta: string;
  emailLabel: string;
  roleLabel: string;
  emailNotificationsLabel: string;
  emailNotificationsHint: string;
  saveButton: string;
  savedMessage: string;
  errorGeneric: string;
  signOutButton: string;
}

export function ProfilePanel({ labels }: { labels: ProfileLabels }) {
  const { user, loading: authLoading, csrfToken, signOut } = useAuth();
  const router = useRouter();
  const [emailNotificationsEnabled, setEmailNotificationsEnabled] = useState(
    user?.email_notifications_enabled ?? false,
  );
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (authLoading) {
    return (
      <p className={styles.loading}>
        <Spinner label={labels.loading} />
        <span aria-hidden="true">{labels.loading}</span>
      </p>
    );
  }

  if (!user) {
    return (
      <Card className={styles.card}>
        <p className={styles.signInTitle}>{labels.signInTitle}</p>
        <Link href="/login">
          <Button>{labels.signInCta}</Button>
        </Link>
      </Card>
    );
  }

  async function handleSave() {
    if (!csrfToken) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    const result = await updateNotificationPreference(csrfToken, emailNotificationsEnabled);
    setSaving(false);
    if (!result.reachable || !result.data) {
      setError(labels.errorGeneric);
      return;
    }
    setSaved(true);
  }

  async function handleSignOut() {
    await signOut();
    router.push("/");
  }

  return (
    <Card className={styles.card}>
      <dl className={styles.factList}>
        <div className={styles.fact}>
          <dt>{labels.emailLabel}</dt>
          <dd>{user.email}</dd>
        </div>
        <div className={styles.fact}>
          <dt>{labels.roleLabel}</dt>
          <dd>{user.role}</dd>
        </div>
      </dl>

      <Switch
        label={labels.emailNotificationsLabel}
        checked={emailNotificationsEnabled}
        onChange={(e) => setEmailNotificationsEnabled(e.target.checked)}
      />
      <p className={styles.hint}>{labels.emailNotificationsHint}</p>

      {error && (
        <p role="alert" className={styles.errorText}>
          {error}
        </p>
      )}
      {saved && (
        <p role="status" className={styles.savedText}>
          {labels.savedMessage}
        </p>
      )}

      <div className={styles.actions}>
        <Button loading={saving} onClick={handleSave}>
          {labels.saveButton}
        </Button>
        <Button variant="secondary" onClick={handleSignOut}>
          {labels.signOutButton}
        </Button>
      </div>
    </Card>
  );
}
