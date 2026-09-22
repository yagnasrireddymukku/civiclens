"use client";

import type { ChangeEvent } from "react";
import type { DeliveryMode, ServiceCategory } from "@civiclens/types";
import { useRouter } from "@/i18n/navigation";
import { Pagination } from "@/components/navigation";
import styles from "./ServiceControls.module.css";

const SERVICE_CATEGORIES: ServiceCategory[] = [
  "CERTIFICATES",
  "DOCUMENTS",
  "WELFARE",
  "EDUCATION",
  "HEALTHCARE",
  "AGRICULTURE",
  "EMPLOYMENT",
  "BUSINESS",
  "TRANSPORT",
  "MUNICIPAL",
  "REVENUE",
  "SOCIAL_SECURITY",
  "IDENTITY",
  "UTILITIES",
  "OTHER",
];

const DELIVERY_MODES: DeliveryMode[] = ["ONLINE", "OFFLINE", "BOTH"];

export interface ServiceControlsProps {
  category: ServiceCategory | undefined;
  deliveryMode: DeliveryMode | undefined;
  categoryLabel: string;
  deliveryModeLabel: string;
  allLabel: string;
  categoryLabels: Record<ServiceCategory, string>;
  deliveryModeLabels: Record<DeliveryMode, string>;
  page: number;
  totalPages: number;
}

/**
 * The only interactive part of the services list page — everything else
 * is server-rendered from `searchParams` (page.tsx), matching
 * `JobControls`'s identical pattern (apps/web/app/[locale]/jobs) so
 * results stay shareable/bookmarkable URLs.
 */
export function ServiceControls({
  category,
  deliveryMode,
  categoryLabel,
  deliveryModeLabel,
  allLabel,
  categoryLabels,
  deliveryModeLabels,
  page,
  totalPages,
}: ServiceControlsProps) {
  const router = useRouter();

  function pushQuery(next: { category?: string; deliveryMode?: string; page?: string }) {
    const nextCategory = "category" in next ? next.category : category;
    const nextDeliveryMode = "deliveryMode" in next ? next.deliveryMode : deliveryMode;
    router.push({
      pathname: "/services",
      query: {
        ...(nextCategory ? { category: nextCategory } : {}),
        ...(nextDeliveryMode ? { delivery_mode: nextDeliveryMode } : {}),
        ...(next.page ? { page: next.page } : {}),
      },
    });
  }

  function handleCategoryChange(event: ChangeEvent<HTMLSelectElement>) {
    pushQuery({ category: event.target.value });
  }

  function handleDeliveryModeChange(event: ChangeEvent<HTMLSelectElement>) {
    pushQuery({ deliveryMode: event.target.value });
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
            {SERVICE_CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {categoryLabels[value]}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.filterLabel}>
          <span>{deliveryModeLabel}</span>
          <select
            value={deliveryMode ?? ""}
            onChange={handleDeliveryModeChange}
            className={styles.select}
          >
            <option value="">{allLabel}</option>
            {DELIVERY_MODES.map((value) => (
              <option key={value} value={value}>
                {deliveryModeLabels[value]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={handlePageChange} />
    </div>
  );
}
