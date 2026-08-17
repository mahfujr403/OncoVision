import { useMutation } from '@tanstack/react-query';
import { createPrediction } from '../services/predictionService';
import type { PredictionRequestOptions } from '@/types';

export interface CreatePredictionVars {
  image: File;
  options?: PredictionRequestOptions;
  onUploadProgress?: (percent: number) => void;
}

export function useCreatePrediction() {
  return useMutation({
    mutationFn: ({ image, options, onUploadProgress }: CreatePredictionVars) =>
      createPrediction(image, options, onUploadProgress),
    retry: false,
  });
}
