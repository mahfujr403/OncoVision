import { axiosInstance } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type { ApiResponse, PredictionResponse, PredictionRequestOptions } from '@/types';

export async function createPrediction(
  image: File,
  options: PredictionRequestOptions = {},
  onUploadProgress?: (percentComplete: number) => void,
): Promise<PredictionResponse> {
  const form = new FormData();
  form.append('image', image);

  if (options.confidence_threshold !== undefined) {
    form.append('confidence_threshold', String(options.confidence_threshold));
  }
  form.append(
    'include_individual_predictions',
    String(options.include_individual_predictions ?? true),
  );
  form.append(
    'include_runtime_statistics',
    String(options.include_runtime_statistics ?? false),
  );
  form.append('save_history', String(options.save_history ?? true));
  if (options.generate_report !== undefined) {
    form.append('generate_report', String(options.generate_report));
  }

  const response = await axiosInstance.post<ApiResponse<PredictionResponse>>(
    API_ENDPOINTS.PREDICTIONS.BASE,
    form,
    {
      // Let the browser set the multipart boundary — do not set Content-Type manually
      onUploadProgress: (evt) => {
        if (onUploadProgress && evt.total) {
          onUploadProgress(Math.round((evt.loaded / evt.total) * 100));
        }
      },
    },
  );

  const envelope = response.data;
  if (!envelope.success || !envelope.data) {
    throw new Error(envelope.message ?? 'Prediction failed');
  }
  return envelope.data;
}

export const predictionService = { createPrediction };
