"use client";

import type { NotificationItem, NotificationType, TrackedItem } from "@civiclens/types";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth";
import { DeadlineBadge, VerificationStatus } from "@/components/civic";
import { Button, Card, Spinner } from "@/components/primitives";
import { Link } from "@/i18n/navigation";
import {
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/lib/notifications";
import {
  getTrackedItems,
  pauseTrackedItem,
  removeTrackedItem,
  resumeTrackedItem,
} from "@/lib/tracking";
import styles from "./page.module.css";

export interface DashboardLabels {
  loading: string;
  signInTitle: string;
  signInBody: string;
  signInCta: string;
  sectionDeadlines: string;
  noDeadlines: string;
  sectionTrackedItems: string;
  sectionNotifications: string;
  errorGeneric: string;
  trackedEmptyState: string;
  statusActive: string;
  statusPaused: string;
  pauseAction: string;
  resumeAction: string;
  removeAction: string;
  deadlineLabel: string;
  unavailableNotice: string;
  notificationsEmptyState: string;
  markAllRead: string;
  markRead: string;
  unreadBadge: string;
  typeDeadlineReminder: string;
  typeChangeDetected: string;
  typeEntityUnavailable: string;
}

const NOTIFICATION_TYPE_LABEL_KEY: Record<NotificationType, keyof DashboardLabels> = {
  DEADLINE_REMINDER: "typeDeadlineReminder",
  CHANGE_DETECTED: "typeChangeDetected",
  ENTITY_NO_LONGER_AVAILABLE: "typeEntityUnavailable",
};

const REMINDER_WINDOW_DAYS = 3;

function deadlineStatus(item: TrackedItem, now: Date): "CLOSED" | "CLOSING_SOON" | "OPEN" {
  if (item.deadline_expired) return "CLOSED";
  if (!item.deadline) return "OPEN";
  const days = (new Date(`${item.deadline}T23:59:59`).getTime() - now.getTime()) / 86_400_000;
  return days <= REMINDER_WINDOW_DAYS ? "CLOSING_SOON" : "OPEN";
}

export function TrackingDashboard({ locale, labels }: { locale: string; labels: DashboardLabels }) {
  const { user, loading: authLoading, csrfToken } = useAuth();
  const [trackedItems, setTrackedItems] = useState<TrackedItem[] | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[] | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    void Promise.all([getTrackedItems(), getNotifications(1, 20)]).then(
      ([trackingResult, notificationsResult]) => {
        if (cancelled) return;
        if (trackingResult.reachable && trackingResult.data) {
          setTrackedItems(trackingResult.data.results);
        } else if (!trackingResult.reachable) {
          setError(labels.errorGeneric);
        }
        if (notificationsResult.reachable && notificationsResult.data) {
          setNotifications(notificationsResult.data.results);
          setUnreadCount(notificationsResult.data.unread_count);
        } else if (!notificationsResult.reachable) {
          setError(labels.errorGeneric);
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [user, labels.errorGeneric]);

  async function handlePauseResume(item: TrackedItem) {
    if (!csrfToken) return;
    setBusyId(item.id);
    const action = item.is_active ? pauseTrackedItem : resumeTrackedItem;
    const result = await action(csrfToken, item.id);
    setBusyId(null);
    if (!result.ok) {
      setError(labels.errorGeneric);
      return;
    }
    setTrackedItems(
      (current) =>
        current?.map((i) => (i.id === item.id ? { ...i, is_active: !item.is_active } : i)) ?? null,
    );
  }

  async function handleRemove(item: TrackedItem) {
    if (!csrfToken) return;
    setBusyId(item.id);
    const result = await removeTrackedItem(csrfToken, item.id);
    setBusyId(null);
    if (!result.ok) {
      setError(labels.errorGeneric);
      return;
    }
    setTrackedItems((current) => current?.filter((i) => i.id !== item.id) ?? null);
  }

  async function handleMarkRead(id: string) {
    if (!csrfToken) return;
    const result = await markNotificationRead(csrfToken, id);
    if (!result.ok) return;
    setNotifications(
      (current) =>
        current?.map((n) => (n.id === id ? { ...n, read_at: result.data.read_at } : n)) ?? null,
    );
    setUnreadCount((count) => Math.max(0, count - 1));
  }

  async function handleMarkAllRead() {
    if (!csrfToken) return;
    const result = await markAllNotificationsRead(csrfToken);
    if (!result.ok) return;
    const now = new Date().toISOString();
    setNotifications(
      (current) => current?.map((n) => ({ ...n, read_at: n.read_at ?? now })) ?? null,
    );
    setUnreadCount(0);
  }

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
      <Card className={styles.signInCard}>
        <p className={styles.signInTitle}>{labels.signInTitle}</p>
        <p>{labels.signInBody}</p>
        <Link href="/login">
          <Button>{labels.signInCta}</Button>
        </Link>
      </Card>
    );
  }

  if (trackedItems === null || notifications === null) {
    return (
      <p className={styles.loading}>
        <Spinner label={labels.loading} />
        <span aria-hidden="true">{labels.loading}</span>
      </p>
    );
  }

  const now = new Date();
  const upcomingDeadlines = trackedItems
    .filter((item) => item.is_active && item.deadline && !item.deadline_expired)
    .sort((a, b) => (a.deadline! < b.deadline! ? -1 : 1));

  return (
    <div className={styles.sections}>
      {error && (
        <p role="alert" className={styles.errorText}>
          {error}
        </p>
      )}

      <section aria-labelledby="deadlines-heading" className={styles.section}>
        <h2 id="deadlines-heading" className={styles.sectionHeading}>
          {labels.sectionDeadlines}
        </h2>
        {upcomingDeadlines.length === 0 ? (
          <p className={styles.emptyState}>{labels.noDeadlines}</p>
        ) : (
          <ul className={styles.list}>
            {upcomingDeadlines.map((item) => (
              <li key={item.id} className={styles.listItem}>
                <Card padded>
                  <div className={styles.itemRow}>
                    <span>
                      {item.route ? <Link href={item.route}>{item.title}</Link> : item.title}
                    </span>
                    <DeadlineBadge status={deadlineStatus(item, now)} />
                  </div>
                  <p className={styles.itemMeta}>
                    {labels.deadlineLabel}:{" "}
                    {new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
                      new Date(`${item.deadline}T00:00:00`),
                    )}
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="tracked-items-heading" className={styles.section}>
        <h2 id="tracked-items-heading" className={styles.sectionHeading}>
          {labels.sectionTrackedItems}
        </h2>
        {trackedItems.length === 0 ? (
          <p className={styles.emptyState}>{labels.trackedEmptyState}</p>
        ) : (
          <ul className={styles.list}>
            {trackedItems.map((item) => (
              <li key={item.id} className={styles.listItem}>
                <Card padded>
                  <div className={styles.itemRow}>
                    <span>
                      {item.route ? <Link href={item.route}>{item.title}</Link> : item.title}
                    </span>
                    {item.verification_status && (
                      <VerificationStatus status={item.verification_status} />
                    )}
                  </div>
                  {!item.still_available && (
                    <p role="status" className={styles.unavailableNotice}>
                      {labels.unavailableNotice}
                    </p>
                  )}
                  <p className={styles.itemMeta}>
                    {item.is_active ? labels.statusActive : labels.statusPaused}
                  </p>
                  <div className={styles.itemActions}>
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={busyId === item.id}
                      onClick={() => handlePauseResume(item)}
                    >
                      {item.is_active ? labels.pauseAction : labels.resumeAction}
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      loading={busyId === item.id}
                      onClick={() => handleRemove(item)}
                    >
                      {labels.removeAction}
                    </Button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="notifications-heading" className={styles.section}>
        <div className={styles.sectionHeadingRow}>
          <h2 id="notifications-heading" className={styles.sectionHeading}>
            {labels.sectionNotifications}
            {unreadCount > 0 && <span className={styles.unreadBadge}>{unreadCount}</span>}
          </h2>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" onClick={handleMarkAllRead}>
              {labels.markAllRead}
            </Button>
          )}
        </div>
        {notifications.length === 0 ? (
          <p className={styles.emptyState}>{labels.notificationsEmptyState}</p>
        ) : (
          <ul className={styles.list}>
            {notifications.map((notification) => (
              <li key={notification.id} className={styles.listItem}>
                <Card padded className={notification.read_at ? undefined : styles.unread}>
                  <p className={styles.itemMeta}>
                    {labels[NOTIFICATION_TYPE_LABEL_KEY[notification.notification_type]]}
                  </p>
                  <p className={styles.notificationTitle}>{notification.title}</p>
                  <p>{notification.body}</p>
                  {!notification.read_at && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleMarkRead(notification.id)}
                    >
                      {labels.markRead}
                    </Button>
                  )}
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
