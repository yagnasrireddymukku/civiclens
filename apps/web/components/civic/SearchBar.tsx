"use client";

import type { ChangeEvent, FormEvent } from "react";
import { Spinner } from "../primitives/Spinner";
import styles from "./SearchBar.module.css";

export type SearchBarState = "idle" | "loading" | "error" | "results-ready";

export interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  state?: SearchBarState;
  placeholder: string;
  errorMessage?: string;
  resultsCount?: number;
  label: string;
}

/**
 * The reusable search UI only — docs/SEARCH.md's engine doesn't exist
 * yet (docs/ROADMAP.md Phase 5), so `onSubmit` has nothing real to call
 * yet. "Empty"/"typing"/"focused" fall out naturally from `value` and
 * CSS `:focus-within`; `state` covers the three states that need
 * explicit visual feedback beyond the input itself.
 */
export function SearchBar({
  value,
  onChange,
  onSubmit,
  state = "idle",
  placeholder,
  errorMessage,
  resultsCount,
  label,
}: SearchBarProps) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    onChange(event.target.value);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(value);
  }

  const statusId = "search-bar-status";

  return (
    <form role="search" onSubmit={handleSubmit} className={styles.form}>
      <div className={styles.field}>
        <input
          type="search"
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          aria-label={label}
          aria-describedby={errorMessage ? statusId : undefined}
          aria-invalid={state === "error" || undefined}
          className={styles.input}
        />
        {state === "loading" && <Spinner size="sm" label="Searching" />}
      </div>
      <div id={statusId} role="status" className={styles.status}>
        {state === "error" && errorMessage}
        {state === "results-ready" &&
          resultsCount !== undefined &&
          `${resultsCount} result${resultsCount === 1 ? "" : "s"}`}
      </div>
    </form>
  );
}
