import { axiosInstance, unwrap } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type { ApiEnvelope, PredictionRequestOptions, PredictionResponse } from '@/types';

/** POST /api/v1/predictions — multipart/form-data, verified against
 *  app/api/v1/predictions/{router,schemas}.py. */
export async function createPrediction(
  imageFile: File,
  options: PredictionRequestOptions,
): Promise<PredictionResponse> {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('confidence_threshold', String(options.confidence_threshold));
  formData.append('include_individual_predictions', String(options.include_individual_predictions));
  formData.append('include_runtime_statistics', String(options.include_runtime_statistics));
  formData.append('save_history', String(options.save_history));
  formData.append('generate_report', String(options.generate_report));

  const response = await axiosInstance.post<ApiEnvelope<PredictionResponse>>(
    API_ENDPOINTS.PREDICTIONS.CREATE,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return unwrap(response.data);
}
