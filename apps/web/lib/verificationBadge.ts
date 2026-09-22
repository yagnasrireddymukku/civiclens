import type { VerificationStatus } from "@civiclens/types";
import type { SourceBadgeKind } from "@/components/civic";

/**
 * Only VERIFIED/NEEDS_REVIEW documents are ever returned by a public API
 * (apps/api's `_INDEXABLE_STATUSES`/`_PUBLIC_VERIFICATION_STATUSES`), but
 * the type is the full four-value enum, so this stays total rather than
 * partial. Shared across every page that renders a `SourceBadge` next to
 * a verification-tracked entity (search results, jobs).
 */
export function toSourceBadgeKind(status: VerificationStatus): SourceBadgeKind {
  return status === "VERIFIED" ? "verified" : "available";
}
