import type {
  AdminDashboardResponse,
  AdminEntityType,
  AdminSourceDetailResponse,
  AdminSourceListResponse,
  ChangeRecordItem,
  ChangeRecordListResponse,
  ChangeReviewStatus,
  VerificationQueueResponse,
  VerificationRecordItem,
  VerificationStatus,
} from "@civiclens/types";
import {
  adminDashboardResponseSchema,
  adminSourceDetailResponseSchema,
  adminSourceListResponseSchema,
  changeRecordItemSchema,
  changeRecordListResponseSchema,
  verificationQueueResponseSchema,
  verificationRecordItemSchema,
} from "@civiclens/validation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type AdminApiResult<T> =
  { reachable: true; data: T } | { reachable: false; error: string; status?: number };

async function adminGet<T>(
  path: string,
  schema: { parse: (data: unknown) => T },
): Promise<AdminApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) {
      return {
        reachable: false,
        error: `API responded with HTTP ${response.status}`,
        status: response.status,
      };
    }
    const payload: unknown = await response.json();
    return { reachable: true, data: schema.parse(payload) };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

async function adminMutate<T>(
  path: string,
  csrfToken: string,
  schema: { parse: (data: unknown) => T },
  body?: Record<string, unknown>,
): Promise<AdminApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) {
      return {
        reachable: false,
        error: `API responded with HTTP ${response.status}`,
        status: response.status,
      };
    }
    const payload: unknown = await response.json();
    return { reachable: true, data: schema.parse(payload) };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error contacting the API",
    };
  }
}

export function getAdminDashboard(): Promise<AdminApiResult<AdminDashboardResponse>> {
  return adminGet("/api/v1/admin/dashboard", adminDashboardResponseSchema);
}

export function getChangeRecords(
  reviewStatus?: ChangeReviewStatus,
  page = 1,
  pageSize = 20,
): Promise<AdminApiResult<ChangeRecordListResponse>> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (reviewStatus) query.set("review_status", reviewStatus);
  return adminGet(
    `/api/v1/admin/change-records?${query.toString()}`,
    changeRecordListResponseSchema,
  );
}

export function approveChangeRecord(
  csrfToken: string,
  id: string,
): Promise<AdminApiResult<ChangeRecordItem>> {
  return adminMutate(
    `/api/v1/admin/change-records/${encodeURIComponent(id)}/approve`,
    csrfToken,
    changeRecordItemSchema,
  );
}

export function rejectChangeRecord(
  csrfToken: string,
  id: string,
): Promise<AdminApiResult<ChangeRecordItem>> {
  return adminMutate(
    `/api/v1/admin/change-records/${encodeURIComponent(id)}/reject`,
    csrfToken,
    changeRecordItemSchema,
  );
}

export function getVerificationQueue(
  entityType?: AdminEntityType,
  page = 1,
  pageSize = 20,
): Promise<AdminApiResult<VerificationQueueResponse>> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (entityType) query.set("entity_type", entityType);
  return adminGet(
    `/api/v1/admin/verification/queue?${query.toString()}`,
    verificationQueueResponseSchema,
  );
}

export function submitVerification(
  csrfToken: string,
  entityType: AdminEntityType,
  entityId: string,
  status: VerificationStatus,
  sourceId: string,
): Promise<AdminApiResult<VerificationRecordItem>> {
  return adminMutate(
    `/api/v1/admin/verification/${entityType}/${encodeURIComponent(entityId)}`,
    csrfToken,
    verificationRecordItemSchema,
    { status, source_id: sourceId },
  );
}

export function getAdminSources(
  page = 1,
  pageSize = 20,
): Promise<AdminApiResult<AdminSourceListResponse>> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return adminGet(`/api/v1/admin/sources?${query.toString()}`, adminSourceListResponseSchema);
}

export function getAdminSourceDetail(
  id: string,
): Promise<AdminApiResult<AdminSourceDetailResponse>> {
  return adminGet(
    `/api/v1/admin/sources/${encodeURIComponent(id)}`,
    adminSourceDetailResponseSchema,
  );
}
