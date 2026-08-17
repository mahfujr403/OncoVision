import { useQuery } from '@tanstack/react-query';
import { reportsService } from '../services/reportsService';
import { QUERY_KEYS } from '@/constants/api';

export function useReportsAnalytics() {
  return useQuery({
    queryKey: QUERY_KEYS.REPORTS.ANALYTICS,
    queryFn: () => reportsService.getAnalytics(),
    staleTime: 2 * 60_000, // 2 min — analytics don't change on every render
    retry: (failureCount, error) => {
      const status = (error as { statusCode?: number }).statusCode;
      if (status === 401) return false;
      return failureCount < 2;
    },
  });
}
