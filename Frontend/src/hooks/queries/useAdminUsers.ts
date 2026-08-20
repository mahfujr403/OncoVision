import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  activateAdminUser,
  deactivateAdminUser,
  fetchAdminUsers,
  type AdminUserListParams,
} from '@/api/services/adminService';
import { QUERY_KEYS } from '@/constants/api';
import { STALE_TIME_MS } from '@/constants/app';

export function useAdminUsers(params: AdminUserListParams) {
  return useQuery({
    queryKey: QUERY_KEYS.ADMIN_USERS(params),
    queryFn: () => fetchAdminUsers(params),
    staleTime: STALE_TIME_MS,
    placeholderData: (prev) => prev,
  });
}

export function useActivateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: activateAdminUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });
}

export function useDeactivateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deactivateAdminUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });
}
