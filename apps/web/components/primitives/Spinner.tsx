import styles from "./Spinner.module.css";

export interface SpinnerProps {
  label?: string;
  size?: "sm" | "md" | "lg";
}

/** An accessible loading indicator — always carries a label for
 * assistive tech, defaulting to a generic one if the caller has
 * nothing more specific to say. */
export function Spinner({ label = "Loading", size = "md" }: SpinnerProps) {
  return (
    <span role="status" className={styles.wrapper}>
      <span className={[styles.spinner, styles[size]].join(" ")} aria-hidden="true" />
      <span className="visually-hidden">{label}</span>
    </span>
  );
}
