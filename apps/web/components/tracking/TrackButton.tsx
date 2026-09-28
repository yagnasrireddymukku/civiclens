"use client";

import type { TrackedEntityType } from "@civiclens/types";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/primitives";
import { getTrackedItems, removeTrackedItem, trackEntity } from "@/lib/tracking";
import styles from "./TrackButton.module.css";

export interface TrackButtonProps {
  entityType: TrackedEntityType;
  entitySlug: string;
}

/**
 * A real, functional tracking control — never an inert placeholder.
 * Signed-out visitors see a link to sign in (never a disabled button
 * pretending the feature is unavailable); signed-in visitors get an
 * actual track/untrack toggle that only ever reflects a server-
 * confirmed state (no optimistic "tracked" flip before the request
 * resolves, per this phase's explicit "never pretend success before
 * server confirms").
 */
export function TrackButton({ entityType, entitySlug }: TrackButtonProps) {
  const t = useTranslations("Tracking");
  const { user, csrfToken, loading: authLoading } = useAuth();
  // `undefined` = not yet checked, `null` = checked and not tracked, a
  // string = checked and tracked (that `TrackedItem.id`). Deriving
  // "still checking" from this single value (rather than a second
  // `checking` flag flipped synchronously in the effect below) avoids a
  // sync `setState` call in the effect body outside its async callback.
  const [trackedItemId, setTrackedItemId] = useState<string | null | undefined>(undefined);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const checking = trackedItemId === undefined;

  useEffect(() => {
    if (!user) return;

    let cancelled = false;
    void getTrackedItems().then((result) => {
      if (cancelled) return;
      if (result.reachable && result.data) {
        const match = result.data.results.find(
          (item) =>
            item.entity_type === entityType &&
            item.is_active &&
            item.route?.endsWith(`/${entitySlug}`),
        );
        setTrackedItemId(match?.id ?? null);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [user, entityType, entitySlug]);

  if (authLoading) {
    return null;
  }

  // Checked ahead of `checking` below: a stale in-flight check from a
  // just-ended session must never block rendering the sign-in prompt.
  if (!user) {
    return (
      <Link href="/login" className={styles.signInPrompt}>
        {t("signInToTrack")}
      </Link>
    );
  }

  if (checking) {
    return null;
  }

  async function handleTrack() {
    if (!csrfToken) return;
    setPending(true);
    setError(null);
    const result = await trackEntity(csrfToken, entityType, entitySlug);
    setPending(false);
    if (!result.reachable) {
      setError(t("errorGeneric"));
      return;
    }
    setTrackedItemId(result.data.id);
  }

  async function handleUntrack() {
    if (!csrfToken || !trackedItemId) return;
    setPending(true);
    setError(null);
    const result = await removeTrackedItem(csrfToken, trackedItemId);
    setPending(false);
    if (!result.ok) {
      setError(t("errorGeneric"));
      return;
    }
    setTrackedItemId(null);
  }

  return (
    <div className={styles.wrapper}>
      {trackedItemId ? (
        <Button variant="secondary" size="sm" loading={pending} onClick={handleUntrack}>
          {t("stopTracking")}
        </Button>
      ) : (
        <Button variant="primary" size="sm" loading={pending} onClick={handleTrack}>
          {t("trackThis")}
        </Button>
      )}
      {error && (
        <p role="alert" className={styles.errorText}>
          {error}
        </p>
      )}
    </div>
  );
}
