import { axiosInstance, unwrap } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type { ApiEnvelope, HistoryQueryParams, PredictionHistoryDetail, PredictionHistoryListResponse } from '@/types';

/** GET /api/v1/predictions/history — verified against
 *  app/api/v1/history/router.py query params. */
export async function fetchPredictionHistory(
  params: HistoryQueryParams,
): Promise<PredictionHistoryListResponse> {
  const response = await axiosInstance.get<ApiEnvelope<PredictionHistoryListResponse>>(
    API_ENDPOINTS.PREDICTIONS.HISTORY,
    { params },
  );
  return unwrap(response.data);
}

/** GET /api/v1/predictions/history/{history_id} */
export async function fetchPredictionHistoryDetail(historyId: string): Promise<PredictionHistoryDetail> {
  const response = await axiosInstance.get<ApiEnvelope<PredictionHistoryDetail>>(
    API_ENDPOINTS.PREDICTIONS.HISTORY_DETAIL(historyId),
  );
  return unwrap(response.data);
}
