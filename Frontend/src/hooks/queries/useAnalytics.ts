import { useQuery } from '@tanstack/react-query';
import { fetchPredictionAnalytics } from '@/api/services/reportsService';
import { QUERY_KEYS } from '@/constants/api';
import { STALE_TIME_MS } from '@/constants/app';

export function useAnalytics() {
  return useQuery({
    queryKey: QUERY_KEYS.ANALYTICS,
    queryFn: fetchPredictionAnalytics,
    staleTime: STALE_TIME_MS,
  });
}
