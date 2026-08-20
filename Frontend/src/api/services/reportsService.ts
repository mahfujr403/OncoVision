import { axiosInstance, unwrap } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type { ApiEnvelope, PredictionAnalytics } from '@/types';

/** GET /api/v1/reports/analytics — verified against app/schemas/reports.py. */
export async function fetchPredictionAnalytics(): Promise<PredictionAnalytics> {
  const response = await axiosInstance.get<ApiEnvelope<PredictionAnalytics>>(API_ENDPOINTS.REPORTS.ANALYTICS);
  return unwrap(response.data);
}

/**
 * Both export endpoints require the Authorization header (handled by the
 * axios interceptor) and stream a file, not the JSON envelope — so we fetch
 * as a blob and trigger the browser download manually rather than using a
 * plain <a href="..."> which wouldn't carry the auth token.
 */
async function downloadFile(url: string, filename: string): Promise<void> {
  const response = await axiosInstance.get(url, { responseType: 'blob' });
  const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export function exportPredictionHistoryCsv(): Promise<void> {
  return downloadFile(API_ENDPOINTS.REPORTS.EXPORT_CSV, `oncovision-history-${Date.now()}.csv`);
}

export function exportPredictionReportPdf(): Promise<void> {
  return downloadFile(API_ENDPOINTS.REPORTS.EXPORT_PDF, `oncovision-report-${Date.now()}.pdf`);
}
