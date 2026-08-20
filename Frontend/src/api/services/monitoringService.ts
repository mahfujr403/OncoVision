import { axiosInstance, unwrap } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type { ApiEnvelope, MonitoringStatus } from '@/types';

/** GET /api/v1/monitoring — verified against app/schemas/monitoring.py. */
export async function fetchMonitoringStatus(): Promise<MonitoringStatus> {
  const response = await axiosInstance.get<ApiEnvelope<MonitoringStatus>>(API_ENDPOINTS.MONITORING);
  return unwrap(response.data);
}
