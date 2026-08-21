import type { ApiErrorEnvelope, PredictionRequestOptions, PredictionResponse } from '@/types/prediction';

/**
 * SIMULATION ONLY.
 *
 * Real backend integration (Axios instance, auth token attachment, actual
 * POST /api/v1/predictions call, TanStack Query mutation) is Phase 5 work
 * per the project roadmap. This module exists so the Phase 2 UI can be
 * exercised end-to-end with response shapes that exactly match the verified
 * backend contract — it does not call any network endpoint and must not be
 * mistaken for real integration.
 *
 * Every field this produces matches PredictionResponse in
 * src/types/prediction.ts. Nothing here is quietly relied upon elsewhere as
 * if it were real data (e.g. Dashboard/History still correctly show
 * "connect to backend" placeholders).
 */

const CLASS_LABELS = [
  'lung_adenocarcinoma',
  'lung_squamous_cell_carcinoma',
  'lung_benign_tissue',
  'colon_adenocarcinoma',
  'colon_benign_tissue',
];

const MODEL_NAMES = ['EfficientNetV2B0_ResNet50_Fusion', 'DenseNet121', 'MobileNetV2'];

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function id() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export interface MockOutcomeControl {
  /** Force a specific outcome for demoing/testing all states. 'random' picks weighted-realistic. */
  forceOutcome?: 'success' | 'partial_success' | 'failed' | 'runtime_unavailable' | 'random';
}

export async function simulatePredictionRequest(
  _file: File,
  options: PredictionRequestOptions,
  control: MockOutcomeControl = {}
): Promise<PredictionResponse> {
  // Simulate network + inference latency.
  await new Promise((res) => setTimeout(res, 1600 + Math.random() * 1200));

  const outcome =
    control.forceOutcome && control.forceOutcome !== 'random'
      ? control.forceOutcome
      : weightedRandomOutcome();

  if (outcome === 'runtime_unavailable') {
    const err: ApiErrorEnvelope = {
      success: false,
      message: 'No production models are currently available to serve predictions.',
      data: null,
      errors: [{ message: 'No production models are currently available to serve predictions.' }],
      request_id: id(),
      timestamp: new Date().toISOString(),
      status: 503,
    };
    throw err;
  }

  const predictedClass = pick(CLASS_LABELS);
  const timestamp = new Date().toISOString();
  const baseMetadata = {
    api_version: 'v1',
    backend_version: '0.9.0-dev',
    model_manifest_version: '2.3.0',
    processing_time_ms: 0,
  };

  if (outcome === 'failed') {
    return {
      prediction_id: id(),
      status: 'failed',
      message: 'All participating models failed to produce a prediction.',
      timestamp,
      result: {
        prediction: '',
        confidence: 0,
        agreement_ratio: 0,
        successful_models: [],
        failed_models: [...MODEL_NAMES],
        participating_models: 0,
      },
      individual_predictions: options.include_individual_predictions ? [] : null,
      runtime_statistics: options.include_runtime_statistics
        ? {
            loaded_models: [],
            failed_models: [...MODEL_NAMES],
            total_models: MODEL_NAMES.length,
            runtime_status: 'degraded',
            loaded_model_count: 0,
            successful_predictions: 0,
            failed_predictions: MODEL_NAMES.length,
            participating_models: 0,
            preprocessing_time_ms: 42,
            total_inference_time_ms: 0,
            total_execution_time_ms: 58,
            overall_processing_time_ms: 58,
          }
        : null,
      metadata: { ...baseMetadata, processing_time_ms: 58 },
    };
  }

  if (outcome === 'partial_success') {
    const model = pick(MODEL_NAMES);
    const failedModels = MODEL_NAMES.filter((m) => m !== model);
    const confidence = 55 + Math.random() * 40;
    const inferenceMs = 180 + Math.random() * 260;

    return {
      prediction_id: id(),
      status: 'partial_success',
      message: 'Only one model produced a usable prediction; ensemble agreement is not available.',
      timestamp,
      result: {
        prediction: predictedClass,
        confidence: Math.round(confidence * 10) / 10,
        agreement_ratio: 0,
        successful_models: [model],
        failed_models: failedModels,
        participating_models: 1,
      },
      individual_predictions: options.include_individual_predictions
        ? [
            {
              model_name: model,
              prediction: predictedClass,
              confidence: Math.round(confidence * 10) / 10,
              inference_time_ms: Math.round(inferenceMs),
            },
          ]
        : null,
      runtime_statistics: options.include_runtime_statistics
        ? {
            loaded_models: [model],
            failed_models: failedModels,
            total_models: MODEL_NAMES.length,
            runtime_status: 'degraded',
            loaded_model_count: 1,
            successful_predictions: 1,
            failed_predictions: failedModels.length,
            participating_models: 1,
            preprocessing_time_ms: 38,
            total_inference_time_ms: Math.round(inferenceMs),
            total_execution_time_ms: Math.round(inferenceMs + 40),
            overall_processing_time_ms: Math.round(inferenceMs + 90),
          }
        : null,
      metadata: { ...baseMetadata, processing_time_ms: Math.round(inferenceMs + 90) },
    };
  }

  // success — 2+ models
  const participating = Math.random() > 0.3 ? MODEL_NAMES.length : MODEL_NAMES.length - 1;
  const successfulModels = MODEL_NAMES.slice(0, participating);
  const failedModels = MODEL_NAMES.slice(participating);
  const perModel = successfulModels.map((m) => ({
    model_name: m,
    prediction: Math.random() > 0.15 ? predictedClass : pick(CLASS_LABELS),
    confidence: Math.round((55 + Math.random() * 42) * 10) / 10,
    inference_time_ms: Math.round(150 + Math.random() * 300),
  }));
  const agreement =
    perModel.filter((p) => p.prediction === predictedClass).length / perModel.length;
  const ensembleConfidence =
    perModel.reduce((sum, p) => sum + p.confidence, 0) / perModel.length;
  const totalInference = perModel.reduce((sum, p) => sum + p.inference_time_ms, 0);

  return {
    prediction_id: id(),
    status: 'success',
    message: 'Prediction completed successfully.',
    timestamp,
    result: {
      prediction: predictedClass,
      confidence: Math.round(ensembleConfidence * 10) / 10,
      agreement_ratio: Math.round(agreement * 100) / 100,
      successful_models: successfulModels,
      failed_models: failedModels,
      participating_models: successfulModels.length,
    },
    individual_predictions: options.include_individual_predictions ? perModel : null,
    runtime_statistics: options.include_runtime_statistics
      ? {
          loaded_models: successfulModels,
          failed_models: failedModels,
          total_models: MODEL_NAMES.length,
          runtime_status: failedModels.length > 0 ? 'degraded' : 'operational',
          loaded_model_count: successfulModels.length,
          successful_predictions: successfulModels.length,
          failed_predictions: failedModels.length,
          participating_models: successfulModels.length,
          preprocessing_time_ms: 45,
          total_inference_time_ms: totalInference,
          total_execution_time_ms: totalInference + 60,
          overall_processing_time_ms: totalInference + 110,
        }
      : null,
    metadata: { ...baseMetadata, processing_time_ms: totalInference + 110 },
  };
}

function weightedRandomOutcome(): 'success' | 'partial_success' | 'failed' | 'runtime_unavailable' {
  const r = Math.random();
  if (r < 0.72) return 'success';
  if (r < 0.88) return 'partial_success';
  if (r < 0.96) return 'failed';
  return 'runtime_unavailable';
}

export function isApiErrorEnvelope(err: unknown): err is ApiErrorEnvelope {
  return typeof err === 'object' && err !== null && 'success' in err && (err as ApiErrorEnvelope).success === false;
}
