import type { ReactElement } from "react";
import { cloneElement, useId } from "react";
import styles from "./Tooltip.module.css";

export interface TooltipProps {
  content: string;
  children: ReactElement<{ "aria-describedby"?: string }>;
}

/**
 * CSS-only (no JS positioning library, no floating-ui dependency): the
 * tooltip is an absolutely-positioned element shown via `:hover`/
 * `:focus-within`, which also makes it work identically for keyboard
 * focus, not just mouse hover. `aria-describedby` links it to the
 * trigger so screen readers announce it regardless of visibility.
 */
export function Tooltip({ content, children }: TooltipProps) {
  const tooltipId = useId();

  return (
    <span className={styles.wrapper}>
      {cloneElement(children, { "aria-describedby": tooltipId })}
      <span role="tooltip" id={tooltipId} className={styles.bubble}>
        {content}
      </span>
    </span>
  );
}
