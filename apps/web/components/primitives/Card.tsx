import type { HTMLAttributes } from "react";
import styles from "./Card.module.css";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
  padded?: boolean;
}

export function Card({ elevated = false, padded = true, className, ...props }: CardProps) {
  return (
    <div
      className={[styles.card, elevated && styles.elevated, padded && styles.padded, className]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );
}
