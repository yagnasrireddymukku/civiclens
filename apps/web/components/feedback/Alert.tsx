import type { ReactNode } from "react";
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  CloseIcon,
  InfoCircleIcon,
  XCircleIcon,
} from "../icons";
import styles from "./Alert.module.css";

export type AlertTone = "success" | "warning" | "error" | "info";

export interface AlertProps {
  tone: AlertTone;
  title: string;
  children?: ReactNode;
  onDismiss?: () => void;
}

const ICONS: Record<AlertTone, typeof CheckCircleIcon> = {
  success: CheckCircleIcon,
  warning: AlertTriangleIcon,
  error: XCircleIcon,
  info: InfoCircleIcon,
};

/**
 * `role="alert"` for error/warning (interrupts assistive tech
 * immediately — reserved for things the user must notice), `role="status"`
 * for success/info (polite announcement). Never relies on color alone:
 * every tone pairs a distinct icon with the text.
 */
export function Alert({ tone, title, children, onDismiss }: AlertProps) {
  const Icon = ICONS[tone];
  const role = tone === "error" || tone === "warning" ? "alert" : "status";

  return (
    <div className={[styles.alert, styles[tone]].join(" ")} role={role}>
      <Icon className={styles.icon} />
      <div className={styles.content}>
        <p className={styles.title}>{title}</p>
        {children && <div className={styles.body}>{children}</div>}
      </div>
      {onDismiss && (
        <button type="button" onClick={onDismiss} className={styles.dismiss} aria-label="Dismiss">
          <CloseIcon />
        </button>
      )}
    </div>
  );
}
