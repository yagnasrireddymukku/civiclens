"use client";

import type { ReactNode } from "react";
import { useEffect, useId, useRef } from "react";
import { CloseIcon } from "../icons";
import styles from "./Dialog.module.css";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

/**
 * Wraps the native `<dialog>` element rather than hand-building a
 * focus-trap: `showModal()` gives a real top-layer modal with built-in
 * focus trapping, `Escape`-to-close, and inert background — for free,
 * with no dependency (this phase's "avoid unnecessary UI libraries" rule).
 */
export function Dialog({ open, onClose, title, children }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (open && !node.open) {
      node.showModal();
    } else if (!open && node.open) {
      node.close();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      className={styles.dialog}
      onClose={onClose}
      onCancel={onClose}
    >
      <div className={styles.header}>
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        <button type="button" onClick={onClose} className={styles.close} aria-label="Close dialog">
          <CloseIcon />
        </button>
      </div>
      <div className={styles.body}>{children}</div>
    </dialog>
  );
}
