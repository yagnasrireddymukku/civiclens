import type { InputHTMLAttributes } from "react";
import { forwardRef, useId } from "react";
import styles from "./Checkbox.module.css";

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, id, className, ...props },
  ref,
) {
  const generatedId = useId();
  const checkboxId = id ?? generatedId;

  return (
    <label htmlFor={checkboxId} className={[styles.wrapper, className].filter(Boolean).join(" ")}>
      <input ref={ref} type="checkbox" id={checkboxId} className={styles.input} {...props} />
      <span className={styles.box} aria-hidden="true">
        <svg viewBox="0 0 16 16" className={styles.check}>
          <path
            d="M3.5 8.5l3 3 6-6"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span className={styles.label}>{label}</span>
    </label>
  );
});
