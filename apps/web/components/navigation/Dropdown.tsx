import type { ReactNode } from "react";
import { ChevronDownIcon } from "../icons";
import styles from "./Dropdown.module.css";

export interface DropdownItem {
  label: string;
  onSelect: () => void;
}

export interface DropdownProps {
  label: ReactNode;
  items: DropdownItem[];
}

/**
 * Built on native `<details>/<summary>` rather than a custom popup:
 * the browser already handles open/close state, click-outside-to-close
 * behavior for free doesn't fully apply here (native details stays open
 * on outside click), but Enter/Space toggling and the disclosure
 * semantics do — a reasonable accessible baseline for a foundation
 * primitive (this phase's scope), refined further only if a real usage
 * needs more (e.g. Escape-to-close, outside-click-to-close).
 */
export function Dropdown({ label, items }: DropdownProps) {
  return (
    <details className={styles.details}>
      <summary className={styles.trigger}>
        {label}
        <ChevronDownIcon className={styles.chevron} />
      </summary>
      <ul className={styles.menu} role="menu">
        {items.map((item) => (
          <li key={item.label} role="none">
            <button
              type="button"
              role="menuitem"
              className={styles.item}
              onClick={(event) => {
                item.onSelect();
                event.currentTarget.closest("details")?.removeAttribute("open");
              }}
            >
              {item.label}
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}
