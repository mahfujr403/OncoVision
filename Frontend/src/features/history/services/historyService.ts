import { axiosInstance } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type { ApiResponse } from '@/types';
import type {
  PredictionHistoryListResponse,
  PredictionHistoryDetail,
  PredictionHistoryFilters,
} from '../types';

function buildParams(filters: PredictionHistoryFilters): Record<string, string | number> {
  const p: Record<string, string | number> = {};
  if (filters.page !== undefined) p.page = filters.page;
  if (filters.page_size !== undefined) p.page_size = filters.page_size;
  if (filters.status) p.status = filters.status;
  if (filters.predicted_class?.trim()) p.predicted_class = filters.predicted_class.trim();
  if (filters.start_date) p.start_date = filters.start_date;
  if (filters.end_date) p.end_date = filters.end_date;
  if (filters.min_confidence !== undefined) p.min_confidence = filters.min_confidence;
  if (filters.max_confidence !== undefined) p.max_confidence = filters.max_confidence;
  return p;
}

export const historyService = {
  async listHistory(filters: PredictionHistoryFilters = {}): Promise<PredictionHistoryListResponse> {
    const res = await axiosInstance.get<ApiResponse<PredictionHistoryListResponse>>(
      API_ENDPOINTS.PREDICTIONS.HISTORY,
      { params: buildParams(filters) },
    );
    const env = res.data;
    if (!env.success || !env.data) throw new Error(env.message ?? 'Failed to load history');
    return env.data;
  },

  async getDetail(historyId: string): Promise<PredictionHistoryDetail> {
    const res = await axiosInstance.get<ApiResponse<PredictionHistoryDetail>>(
      API_ENDPOINTS.PREDICTIONS.HISTORY_BY_ID(historyId),
    );
    const env = res.data;
    if (!env.success || !env.data) throw new Error(env.message ?? 'Record not found');
    return env.data;
  },
};
