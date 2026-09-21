"use client";

import type { KeyboardEvent, ReactNode } from "react";
import { useId, useState } from "react";
import styles from "./Tabs.module.css";

export interface TabItem {
  value: string;
  label: string;
  content: ReactNode;
}

export interface TabsProps {
  label: string;
  items: TabItem[];
  defaultValue?: string;
}

/**
 * Hand-rolled per the WAI-ARIA tabs pattern: `role="tablist"`/`"tab"`/
 * `"tabpanel"`, one tab in the Tab order at a time (roving tabindex),
 * Left/Right arrow keys move focus between tabs, Home/End jump to the
 * first/last.
 */
export function Tabs({ label, items, defaultValue }: TabsProps) {
  const [active, setActive] = useState(defaultValue ?? items[0]?.value);
  const baseId = useId();

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % items.length;
    else if (event.key === "ArrowLeft") nextIndex = (index - 1 + items.length) % items.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = items.length - 1;

    if (nextIndex !== null) {
      event.preventDefault();
      const nextItem = items[nextIndex];
      setActive(nextItem.value);
      document.getElementById(`${baseId}-tab-${nextItem.value}`)?.focus();
    }
  }

  return (
    <div>
      <div role="tablist" aria-label={label} className={styles.list}>
        {items.map((item, index) => {
          const selected = item.value === active;
          return (
            <button
              key={item.value}
              role="tab"
              id={`${baseId}-tab-${item.value}`}
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${item.value}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(item.value)}
              onKeyDown={(event) => handleKeyDown(event, index)}
              className={[styles.tab, selected && styles.tabActive].filter(Boolean).join(" ")}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {items.map((item) => (
        <div
          key={item.value}
          role="tabpanel"
          id={`${baseId}-panel-${item.value}`}
          aria-labelledby={`${baseId}-tab-${item.value}`}
          hidden={item.value !== active}
          className={styles.panel}
          tabIndex={0}
        >
          {item.content}
        </div>
      ))}
    </div>
  );
}
