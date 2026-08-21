import { useQuery } from '@tanstack/react-query';
import { fetchAdminSystemStatus } from '@/api/services/adminService';
import { QUERY_KEYS } from '@/constants/api';

export function useAdminSystem() {
  return useQuery({
    queryKey: QUERY_KEYS.ADMIN_SYSTEM,
    queryFn: fetchAdminSystemStatus,
    staleTime: 30_000, // system health should feel reasonably fresh
    refetchInterval: 30_000,
  });
}
