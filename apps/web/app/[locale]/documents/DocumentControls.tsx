"use client";

import type { ChangeEvent } from "react";
import type { DocumentCategory, DocumentType } from "@civiclens/types";
import { useRouter } from "@/i18n/navigation";
import { Pagination } from "@/components/navigation";
import styles from "./DocumentControls.module.css";

const DOCUMENT_TYPES: DocumentType[] = [
  "CERTIFICATE",
  "IDENTITY_DOCUMENT",
  "RECORD",
  "PERMIT",
  "LICENSE",
  "REGISTRATION",
  "OTHER",
];

const DOCUMENT_CATEGORIES: DocumentCategory[] = [
  "PERSONAL",
  "IDENTITY",
  "RESIDENCE",
  "INCOME",
  "SOCIAL_CATEGORY",
  "EDUCATION",
  "BIRTH_DEATH",
  "DISABILITY",
  "LAND_REVENUE",
  "EMPLOYMENT",
  "BUSINESS",
  "FAMILY",
  "OTHER",
];

export interface DocumentControlsProps {
  documentType: DocumentType | undefined;
  category: DocumentCategory | undefined;
  documentTypeLabel: string;
  categoryLabel: string;
  allLabel: string;
  documentTypeLabels: Record<DocumentType, string>;
  categoryLabels: Record<DocumentCategory, string>;
  page: number;
  totalPages: number;
}

/**
 * The only interactive part of the documents list page — everything
 * else is server-rendered from `searchParams` (page.tsx), matching
 * `SchemeControls`'s identical pattern (apps/web/app/[locale]/schemes)
 * so results stay shareable/bookmarkable URLs.
 */
export function DocumentControls({
  documentType,
  category,
  documentTypeLabel,
  categoryLabel,
  allLabel,
  documentTypeLabels,
  categoryLabels,
  page,
  totalPages,
}: DocumentControlsProps) {
  const router = useRouter();

  function pushQuery(next: { documentType?: string; category?: string; page?: string }) {
    const nextDocumentType = "documentType" in next ? next.documentType : documentType;
    const nextCategory = "category" in next ? next.category : category;
    router.push({
      pathname: "/documents",
      query: {
        ...(nextDocumentType ? { document_type: nextDocumentType } : {}),
        ...(nextCategory ? { category: nextCategory } : {}),
        ...(next.page ? { page: next.page } : {}),
      },
    });
  }

  function handleDocumentTypeChange(event: ChangeEvent<HTMLSelectElement>) {
    pushQuery({ documentType: event.target.value });
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
          <span>{documentTypeLabel}</span>
          <select
            value={documentType ?? ""}
            onChange={handleDocumentTypeChange}
            className={styles.select}
          >
            <option value="">{allLabel}</option>
            {DOCUMENT_TYPES.map((value) => (
              <option key={value} value={value}>
                {documentTypeLabels[value]}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.filterLabel}>
          <span>{categoryLabel}</span>
          <select value={category ?? ""} onChange={handleCategoryChange} className={styles.select}>
            <option value="">{allLabel}</option>
            {DOCUMENT_CATEGORIES.map((value) => (
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
