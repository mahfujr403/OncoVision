import { useQuery } from '@tanstack/react-query';
import { historyService } from '../services/historyService';
import { QUERY_KEYS } from '@/constants/api';
import type { PredictionHistoryFilters } from '../types';

export function useHistoryList(filters: PredictionHistoryFilters = {}) {
  return useQuery({
    queryKey: QUERY_KEYS.HISTORY.LIST(filters as Record<string, unknown>),
    queryFn: () => historyService.listHistory(filters),
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  });
}

export function useHistoryDetail(historyId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.HISTORY.DETAIL(historyId),
    queryFn: () => historyService.getDetail(historyId),
    enabled: Boolean(historyId),
    staleTime: 5 * 60_000,
    retry: (failureCount, error) => {
      const status = (error as { statusCode?: number }).statusCode;
      if (status === 404) return false;
      return failureCount < 2;
    },
  });
}
