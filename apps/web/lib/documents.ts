import type {
  DeliveryMode,
  DocumentCategory,
  DocumentDetail,
  DocumentListResponse,
  DocumentType,
} from "@civiclens/types";
import { documentDetailSchema, documentListResponseSchema } from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface DocumentListParams {
  page?: number;
  documentType?: DocumentType;
  category?: DocumentCategory;
  deliveryMode?: DeliveryMode;
}

export type DocumentListApiResult =
  { reachable: true; data: DocumentListResponse } | { reachable: false; error: string };

export type DocumentDetailApiResult =
  | { reachable: true; data: DocumentDetail }
  | { reachable: false; error: string }
  | { reachable: true; data: null };

/**
 * Calls the backend's `GET /api/v1/documents` (docs/API.md §17,
 * docs/DATABASE.md §14). Deliberately never throws — same defensive
 * posture as `getApiHealth`/`getJobs`/`getServices`/`getSchemes`
 * (lib/api.ts, lib/jobs.ts, lib/services.ts, lib/schemes.ts).
 */
export async function getDocuments({
  page = 1,
  documentType,
  category,
  deliveryMode,
}: DocumentListParams): Promise<DocumentListApiResult> {
  try {
    const query = new URLSearchParams({ page: String(page) });
    if (documentType) query.set("document_type", documentType);
    if (category) query.set("category", category);
    if (deliveryMode) query.set("delivery_mode", deliveryMode);

    const response = await fetch(`${API_BASE_URL}/api/v1/documents?${query.toString()}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = documentListResponseSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

/**
 * Calls `GET /api/v1/documents/{slug}`. A 404 is not an error state —
 * it means "no such document" (or, indistinguishably to the public,
 * "not yet published") and is reported as `{ reachable: true; data:
 * null }` so callers can render a not-found page rather than an error
 * banner.
 */
export async function getDocumentBySlug(slug: string): Promise<DocumentDetailApiResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${encodeURIComponent(slug)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (response.status === 404) {
      return { reachable: true, data: null };
    }
    if (!response.ok) {
      return { reachable: false, error: `API responded with HTTP ${response.status}` };
    }

    const payload: unknown = await response.json();
    const data = documentDetailSchema.parse(payload);
    return { reachable: true, data };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}
