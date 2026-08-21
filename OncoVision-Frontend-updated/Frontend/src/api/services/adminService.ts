import { axiosInstance, unwrap } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type {
  AdminHistoryDetail,
  AdminHistoryItem,
  AdminSystemStatus,
  AdminUserListResponse,
  ApiEnvelope,
  HistoryQueryParams,
  User,
} from '@/types';

// IMPORTANT: verified against app/api/v1/admin/users.py — the endpoint only
// accepts `page` and `page_size`. There is NO server-side is_active/role/
// search filter today. AdminUsersPage adjusts for this by filtering the
// already-fetched page client-side (see that page's comments) rather than
// pretending the backend supports a filter it doesn't.
export interface AdminUserListParams {
  page?: number;
  page_size?: number;
}

/** GET /api/v1/admin/users — verified against app/api/v1/admin/users.py. */
export async function fetchAdminUsers(params: AdminUserListParams): Promise<AdminUserListResponse> {
  const response = await axiosInstance.get<ApiEnvelope<AdminUserListResponse>>(API_ENDPOINTS.ADMIN.USERS, {
    params,
  });
  return unwrap(response.data);
}

export async function fetchAdminUser(userId: string): Promise<User> {
  const response = await axiosInstance.get<ApiEnvelope<User>>(API_ENDPOINTS.ADMIN.USER_DETAIL(userId));
  return unwrap(response.data);
}

export async function activateAdminUser(userId: string): Promise<User> {
  const response = await axiosInstance.post<ApiEnvelope<User>>(API_ENDPOINTS.ADMIN.USER_ACTIVATE(userId));
  return unwrap(response.data);
}

export async function deactivateAdminUser(userId: string): Promise<User> {
  const response = await axiosInstance.post<ApiEnvelope<User>>(API_ENDPOINTS.ADMIN.USER_DEACTIVATE(userId));
  return unwrap(response.data);
}

export interface AdminHistoryQueryParams extends HistoryQueryParams {
  /** Admin-only filter, verified in app/api/v1/admin/history.py. */
  user_id?: string;
}

/** GET /api/v1/admin/history — cross-user prediction history. */
export async function fetchAdminHistory(
  params: AdminHistoryQueryParams,
): Promise<{ items: AdminHistoryItem[]; count: number; pagination: AdminUserListResponse['pagination'] }> {
  const response = await axiosInstance.get<
    ApiEnvelope<{ items: AdminHistoryItem[]; count: number; pagination: AdminUserListResponse['pagination'] }>
  >(API_ENDPOINTS.ADMIN.HISTORY, { params });
  return unwrap(response.data);
}

export async function fetchAdminHistoryDetail(historyId: string): Promise<AdminHistoryDetail> {
  const response = await axiosInstance.get<ApiEnvelope<AdminHistoryDetail>>(
    API_ENDPOINTS.ADMIN.HISTORY_DETAIL(historyId),
  );
  return unwrap(response.data);
}

/** GET /api/v1/admin/system — verified against app/schemas/admin.py AdminSystemStatusSchema. */
export async function fetchAdminSystemStatus(): Promise<AdminSystemStatus> {
  const response = await axiosInstance.get<ApiEnvelope<AdminSystemStatus>>(API_ENDPOINTS.ADMIN.SYSTEM);
  return unwrap(response.data);
}
