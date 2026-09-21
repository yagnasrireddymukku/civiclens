import styles from "./Divider.module.css";

export interface DividerProps {
  orientation?: "horizontal" | "vertical";
  label?: string;
}

export function Divider({ orientation = "horizontal", label }: DividerProps) {
  if (label) {
    return (
      <div role="separator" aria-orientation={orientation} className={styles.withLabel}>
        <span className={styles.line} />
        <span className={styles.label}>{label}</span>
        <span className={styles.line} />
      </div>
    );
  }

  return (
    <hr
      className={orientation === "vertical" ? styles.vertical : styles.horizontal}
      aria-orientation={orientation}
    />
  );
}
