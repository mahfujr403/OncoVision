import { useQuery } from '@tanstack/react-query';
import { fetchAdminHistory, fetchAdminHistoryDetail, type AdminHistoryQueryParams } from '@/api/services/adminService';
import { QUERY_KEYS } from '@/constants/api';
import { STALE_TIME_MS } from '@/constants/app';

/** All prediction history across every user (optionally narrowed to one
 *  user via `params.user_id`) — admin-only, backed by `GET /admin/history`. */
export function useAdminHistory(params: AdminHistoryQueryParams) {
  return useQuery({
    queryKey: QUERY_KEYS.ADMIN_HISTORY(params),
    queryFn: () => fetchAdminHistory(params),
    staleTime: STALE_TIME_MS,
    placeholderData: (prev) => prev, // keep old page visible while the next page loads
  });
}

export function useAdminHistoryDetail(historyId: string | undefined) {
  return useQuery({
    queryKey: ['admin', 'history', historyId ?? ''] as const,
    queryFn: () => fetchAdminHistoryDetail(historyId as string),
    enabled: Boolean(historyId),
    staleTime: STALE_TIME_MS,
  });
}
