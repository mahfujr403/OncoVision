import { axiosInstance } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type { ApiResponse } from '@/types';
import type { AnalyticsData } from '../types';

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export const reportsService = {
  async getAnalytics(): Promise<AnalyticsData> {
    const res = await axiosInstance.get<ApiResponse<AnalyticsData>>(
      API_ENDPOINTS.REPORTS.ANALYTICS,
    );
    const env = res.data;
    if (!env.success || !env.data) {
      throw new Error(env.message ?? 'Failed to load analytics');
    }
    return env.data;
  },

  async exportCsv(): Promise<void> {
    const res = await axiosInstance.get<Blob>(API_ENDPOINTS.REPORTS.EXPORT_CSV, {
      responseType: 'blob',
    });
    triggerBlobDownload(res.data, 'oncovision-predictions.csv');
  },

  async exportPdf(): Promise<void> {
    const res = await axiosInstance.get<Blob>(API_ENDPOINTS.REPORTS.EXPORT_PDF, {
      responseType: 'blob',
    });
    triggerBlobDownload(res.data, 'oncovision-report.pdf');
  },
};
