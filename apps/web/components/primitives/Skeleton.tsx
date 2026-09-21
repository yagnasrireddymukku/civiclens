import styles from "./Skeleton.module.css";

export interface SkeletonProps {
  width?: string;
  height?: string;
  circle?: boolean;
  className?: string;
}

/** A loading placeholder. Decorative — the real loading state is
 * announced separately (e.g. a `Spinner` with accessible text, or the
 * containing region's `aria-busy`), so this carries `aria-hidden`. */
export function Skeleton({
  width = "100%",
  height = "1rem",
  circle = false,
  className,
}: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={[styles.skeleton, circle && styles.circle, className].filter(Boolean).join(" ")}
      style={{ width, height }}
    />
  );
}
