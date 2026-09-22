"use client";

import type { ChangeEvent } from "react";
import type { EducationLevel, SchemeCategory } from "@civiclens/types";
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

const EDUCATION_LEVELS: EducationLevel[] = [
  "SCHOOL",
  "INTERMEDIATE",
  "DIPLOMA",
  "UNDERGRADUATE",
  "POSTGRADUATE",
  "DOCTORAL",
  "PROFESSIONAL",
  "VOCATIONAL",
  "OTHER",
];

export interface SchemeControlsProps {
  category: SchemeCategory | undefined;
  educationLevel: EducationLevel | undefined;
  categoryLabel: string;
  educationLevelLabel: string;
  allLabel: string;
  categoryLabels: Record<SchemeCategory, string>;
  educationLevelLabels: Record<EducationLevel, string>;
  page: number;
  totalPages: number;
}

/**
 * The only interactive part of the schemes list page — everything else
 * is server-rendered from `searchParams` (page.tsx), matching
 * `ServiceControls`'s identical pattern (apps/web/app/[locale]/services).
 * Two filters as of Phase 9: category (every scheme) and education
 * level (Phase 9's scholarship-discovery filter, §18 — only matches
 * schemes with a `ScholarshipDetail` row; shown unconditionally rather
 * than only when `category=SCHOLARSHIP` is selected, to keep this
 * component simple, per this phase's "do not build an overly complex
 * filtering system" instruction — combining it with a non-scholarship
 * category simply yields zero results, same as the backend).
 */
export function SchemeControls({
  category,
  educationLevel,
  categoryLabel,
  educationLevelLabel,
  allLabel,
  categoryLabels,
  educationLevelLabels,
  page,
  totalPages,
}: SchemeControlsProps) {
  const router = useRouter();

  function pushQuery(next: { category?: string; educationLevel?: string; page?: string }) {
    const nextCategory = "category" in next ? next.category : category;
    const nextEducationLevel = "educationLevel" in next ? next.educationLevel : educationLevel;
    router.push({
      pathname: "/schemes",
      query: {
        ...(nextCategory ? { category: nextCategory } : {}),
        ...(nextEducationLevel ? { education_level: nextEducationLevel } : {}),
        ...(next.page ? { page: next.page } : {}),
      },
    });
  }

  function handleCategoryChange(event: ChangeEvent<HTMLSelectElement>) {
    pushQuery({ category: event.target.value });
  }

  function handleEducationLevelChange(event: ChangeEvent<HTMLSelectElement>) {
    pushQuery({ educationLevel: event.target.value });
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
        <label className={styles.filterLabel}>
          <span>{educationLevelLabel}</span>
          <select
            value={educationLevel ?? ""}
            onChange={handleEducationLevelChange}
            className={styles.select}
          >
            <option value="">{allLabel}</option>
            {EDUCATION_LEVELS.map((value) => (
              <option key={value} value={value}>
                {educationLevelLabels[value]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={handlePageChange} />
    </div>
  );
}
