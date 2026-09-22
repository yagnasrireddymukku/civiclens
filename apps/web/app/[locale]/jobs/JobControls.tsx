"use client";

import type { ChangeEvent } from "react";
import type { EmploymentType } from "@civiclens/types";
import { useRouter } from "@/i18n/navigation";
import { Pagination } from "@/components/navigation";
import styles from "./JobControls.module.css";

const EMPLOYMENT_TYPES: EmploymentType[] = ["PERMANENT", "CONTRACT", "TEMPORARY"];

export interface JobControlsProps {
  employmentType: EmploymentType | undefined;
  employmentTypeLabel: string;
  allLabel: string;
  employmentTypeLabels: Record<EmploymentType, string>;
  page: number;
  totalPages: number;
}

/**
 * The only interactive part of the jobs list page — everything else is
 * server-rendered from `searchParams` (page.tsx), matching the search
 * page's `SearchControls` pattern (apps/web/app/[locale]/search) so
 * results stay shareable/bookmarkable URLs.
 */
export function JobControls({
  employmentType,
  employmentTypeLabel,
  allLabel,
  employmentTypeLabels,
  page,
  totalPages,
}: JobControlsProps) {
  const router = useRouter();

  function handleEmploymentTypeChange(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    router.push({
      pathname: "/jobs",
      query: value ? { employment_type: value } : {},
    });
  }

  function handlePageChange(nextPage: number) {
    router.push({
      pathname: "/jobs",
      query: {
        ...(employmentType ? { employment_type: employmentType } : {}),
        page: String(nextPage),
      },
    });
  }

  return (
    <div className={styles.controls}>
      <label className={styles.filterLabel}>
        <span>{employmentTypeLabel}</span>
        <select
          value={employmentType ?? ""}
          onChange={handleEmploymentTypeChange}
          className={styles.select}
        >
          <option value="">{allLabel}</option>
          {EMPLOYMENT_TYPES.map((value) => (
            <option key={value} value={value}>
              {employmentTypeLabels[value]}
            </option>
          ))}
        </select>
      </label>
      <Pagination page={page} totalPages={totalPages} onPageChange={handlePageChange} />
    </div>
  );
}
