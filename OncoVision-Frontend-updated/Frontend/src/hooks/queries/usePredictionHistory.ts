import { useQuery } from '@tanstack/react-query';
import { fetchPredictionHistory, fetchPredictionHistoryDetail } from '@/api/services/historyService';
import { QUERY_KEYS } from '@/constants/api';
import { STALE_TIME_MS } from '@/constants/app';
import type { HistoryQueryParams } from '@/types';

export function usePredictionHistory(params: HistoryQueryParams) {
  return useQuery({
    queryKey: QUERY_KEYS.PREDICTION_HISTORY(params),
    queryFn: () => fetchPredictionHistory(params),
    staleTime: STALE_TIME_MS,
    placeholderData: (prev) => prev, // keep old page visible while the next page loads
  });
}

export function usePredictionHistoryDetail(historyId: string | undefined) {
  return useQuery({
    queryKey: QUERY_KEYS.PREDICTION_HISTORY_DETAIL(historyId ?? ''),
    queryFn: () => fetchPredictionHistoryDetail(historyId as string),
    enabled: Boolean(historyId),
    staleTime: STALE_TIME_MS,
  });
}
