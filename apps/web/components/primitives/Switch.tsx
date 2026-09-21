import type { InputHTMLAttributes } from "react";
import { forwardRef, useId } from "react";
import styles from "./Switch.module.css";

export interface SwitchProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
}

/**
 * A native checkbox with `role="switch"` (ARIA 1.2, well-supported) —
 * screen readers announce it as a switch while keyboard/click behavior
 * stays exactly what a checkbox already provides for free.
 */
export const Switch = forwardRef<HTMLInputElement, SwitchProps>(function Switch(
  { label, id, className, ...props },
  ref,
) {
  const generatedId = useId();
  const switchId = id ?? generatedId;

  return (
    <label htmlFor={switchId} className={[styles.wrapper, className].filter(Boolean).join(" ")}>
      <input
        ref={ref}
        type="checkbox"
        role="switch"
        id={switchId}
        className={styles.input}
        {...props}
      />
      <span className={styles.track} aria-hidden="true">
        <span className={styles.thumb} />
      </span>
      <span className={styles.label}>{label}</span>
    </label>
  );
});
