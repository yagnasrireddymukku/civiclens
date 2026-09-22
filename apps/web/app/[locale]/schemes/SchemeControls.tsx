"use client";

import type { ChangeEvent } from "react";
import type { SchemeCategory } from "@civiclens/types";
import { useRouter } from "@/i18n/navigation";
import { Pagination } from "@/components/navigation";
import styles from "./SchemeControls.module.css";

const SCHEME_CATEGORIES: SchemeCategory[] = [
  "SCHOLARSHIP",
  "PENSION",
  "SUBSIDY",
  "FINANCIAL_ASSISTANCE",
  "INSURANCE",
  "HOUSING",
  "HEALTHCARE",
  "EDUCATION",
  "AGRICULTURE",
  "EMPLOYMENT",
  "SKILL_DEVELOPMENT",
  "WOMEN_CHILD_WELFARE",
  "SOCIAL_WELFARE",
  "BUSINESS_ENTREPRENEURSHIP",
  "DISABILITY_SUPPORT",
  "OTHER",
];

export interface SchemeControlsProps {
  category: SchemeCategory | undefined;
  categoryLabel: string;
  allLabel: string;
  categoryLabels: Record<SchemeCategory, string>;
  page: number;
  totalPages: number;
}

/**
 * The only interactive part of the schemes list page — everything else
 * is server-rendered from `searchParams` (page.tsx), matching
 * `ServiceControls`'s identical pattern (apps/web/app/[locale]/services)
 * so results stay shareable/bookmarkable URLs. Only one filter (unlike
 * Services' category + delivery mode): a scheme has no delivery-mode
 * equivalent field.
 */
export function SchemeControls({
  category,
  categoryLabel,
  allLabel,
  categoryLabels,
  page,
  totalPages,
}: SchemeControlsProps) {
  const router = useRouter();

  function pushQuery(next: { category?: string; page?: string }) {
    const nextCategory = "category" in next ? next.category : category;
    router.push({
      pathname: "/schemes",
      query: {
        ...(nextCategory ? { category: nextCategory } : {}),
        ...(next.page ? { page: next.page } : {}),
      },
    });
  }

  function handleCategoryChange(event: ChangeEvent<HTMLSelectElement>) {
    pushQuery({ category: event.target.value });
  }

  function handlePageChange(nextPage: number) {
    pushQuery({ page: String(nextPage) });
  }

  return (
    <div className={styles.controls}>
      <div className={styles.filters}>
        <label className={styles.filterLabel}>
          <span>{categoryLabel}</span>
          <select value={category ?? ""} onChange={handleCategoryChange} className={styles.select}>
            <option value="">{allLabel}</option>
            {SCHEME_CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {categoryLabels[value]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={handlePageChange} />
    </div>
  );
}
