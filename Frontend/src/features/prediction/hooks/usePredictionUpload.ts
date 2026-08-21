import { useState, useCallback, useEffect, useRef } from 'react';
import type { FileRejection } from 'react-dropzone';
import { ACCEPTED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES, MAX_IMAGE_SIZE_MB } from '@/constants/app';
import { createPrediction } from '@/api/services/predictionService';
import type { ApiError, PredictionResponse } from '@/types';
import type {
  ImageMeta,
  ValidationError,
  UploadState,
  PredictionConfig,
  AnalyzeStepInfo,
} from '../types';

const ACCEPTED_MIME_TYPES = Object.keys(ACCEPTED_IMAGE_TYPES) as string[];

function getExtension(mimeType: string): string {
  const map: Record<string, string> = {
    'image/jpeg': 'JPG',
    'image/png': 'PNG',
    'image/tiff': 'TIFF',
  };
  return map[mimeType] ?? mimeType.split('/')[1]?.toUpperCase() ?? '?';
}

async function resolveImageDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight });
      URL.revokeObjectURL(url);
    };
    img.onerror = () => {
      resolve({ width: 0, height: 0 });
      URL.revokeObjectURL(url);
    };
    img.src = url;
  });
}

function validateFile(file: File): ValidationError | null {
  if (file.size === 0) {
    return { code: 'empty', message: 'The selected file is empty. Please choose a valid image.' };
  }
  if (!ACCEPTED_MIME_TYPES.includes(file.type)) {
    return {
      code: 'type',
      message: `Unsupported file type "${file.type || file.name.split('.').pop()}". Use JPG, PNG, or TIFF.`,
    };
  }
  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    return {
      code: 'size',
      message: `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum allowed is ${MAX_IMAGE_SIZE_MB} MB.`,
    };
  }
  return null;
}

const INITIAL_STEPS: AnalyzeStepInfo[] = [
  { id: 'upload', label: 'Upload Complete', status: 'pending' },
  { id: 'prepare', label: 'Preparing Image', status: 'pending' },
  { id: 'request', label: 'Sending Request', status: 'pending' },
  { id: 'waiting', label: 'Waiting for AI', status: 'pending' },
];

const DEFAULT_CONFIG: PredictionConfig = {
  confidenceThreshold: 0.99, // per-project default; backend's own default is 0.5 but this is only a flagging threshold, never sent as anything but an explicit value the user can still adjust
  includeIndividualPredictions: true,
  includeRuntimeStatistics: true,
  saveHistory: true,
  generateReport: false,
  imageSize: '224 × 224 px', // real model input size for every model in the current manifest
};

export function usePredictionUpload() {
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [imageMeta, setImageMeta] = useState<ImageMeta | null>(null);
  const [validationError, setValidationError] = useState<ValidationError | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeSteps, setAnalyzeSteps] = useState<AnalyzeStepInfo[]>(INITIAL_STEPS);
  const [config, setConfig] = useState<PredictionConfig>(DEFAULT_CONFIG);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [predictionError, setPredictionError] = useState<ApiError | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  // Revoke stale object URL on unmount
  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  const processFile = useCallback(async (file: File) => {
    setUploadState('validating');
    setValidationError(null);

    const error = validateFile(file);
    if (error) {
      setValidationError(error);
      setUploadState('error');
      return;
    }

    // Revoke old preview
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);

    const previewUrl = URL.createObjectURL(file);
    previewUrlRef.current = previewUrl;

    const { width, height } = await resolveImageDimensions(file);

    setImageMeta({
      file,
      previewUrl,
      width,
      height,
      sizeBytes: file.size,
      mimeType: file.type,
      ext: getExtension(file.type),
    });
    setUploadState('ready');
    // NOTE: config.imageSize intentionally does NOT track the uploaded
    // file's raw pixel dimensions (those are shown separately from
    // imageMeta.width/height, e.g. in the image preview). This field
    // represents the AI runtime's fixed model input size — 224x224 for
    // every model in the current manifest (verified in
    // app/ml/manifest/models.json) — which never changes per upload.
  }, []);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejections: FileRejection[]) => {
      setUploadState('idle');
      if (rejections.length > 0) {
        const first = rejections[0].errors[0];
        const code = first.code === 'file-too-large' ? 'size' : first.code === 'file-invalid-type' ? 'type' : 'unknown';
        setValidationError({ code: code as ValidationError['code'], message: first.message });
        setUploadState('error');
        return;
      }
      const file = acceptedFiles[0];
      if (file) void processFile(file);
    },
    [processFile],
  );

  const onDragEnter = useCallback(() => setUploadState('dragging'), []);
  const onDragLeave = useCallback(() => {
    setUploadState((s) => (s === 'dragging' ? 'idle' : s));
  }, []);

  // Paste handler — attach globally when no image loaded
  useEffect(() => {
    if (imageMeta) return;
    const handler = (e: ClipboardEvent) => {
      const item = Array.from(e.clipboardData?.items ?? []).find((i) => i.kind === 'file');
      if (!item) return;
      const file = item.getAsFile();
      if (file) void processFile(file);
    };
    window.addEventListener('paste', handler);
    return () => window.removeEventListener('paste', handler);
  }, [imageMeta, processFile]);

  const removeImage = useCallback(() => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setImageMeta(null);
    setValidationError(null);
    setUploadState('idle');
    setIsAnalyzing(false);
    setAnalyzeSteps(INITIAL_STEPS);
    setResult(null);
    setPredictionError(null);
  }, []);

  const updateStep = (id: AnalyzeStepInfo['id'], status: AnalyzeStepInfo['status']) => {
    setAnalyzeSteps((steps) => steps.map((s) => (s.id === id ? { ...s, status } : s)));
  };

  // Real analyze flow: POST /api/v1/predictions (multipart). The step
  // indicators are cosmetic — the backend does not stream progress — so
  // 'upload'/'prepare' resolve immediately and 'request'/'waiting' track the
  // actual in-flight request rather than a fixed delay.
  const analyze = useCallback(async () => {
    if (!imageMeta || isAnalyzing) return;
    setIsAnalyzing(true);
    setAnalyzeSteps(INITIAL_STEPS);
    setResult(null);
    setPredictionError(null);

    updateStep('upload', 'done');
    updateStep('prepare', 'done');
    updateStep('request', 'active');

    try {
      const response = await createPrediction(imageMeta.file, {
        confidence_threshold: config.confidenceThreshold,
        include_individual_predictions: config.includeIndividualPredictions,
        include_runtime_statistics: config.includeRuntimeStatistics,
        save_history: config.saveHistory,
        generate_report: config.generateReport,
      });
      updateStep('request', 'done');
      updateStep('waiting', 'done');
      setResult(response);
    } catch (err) {
      updateStep('request', 'error');
      setPredictionError(err as ApiError);
    } finally {
      setIsAnalyzing(false);
    }
  }, [imageMeta, isAnalyzing, config]);

  const setConfidenceThreshold = useCallback((value: number) => {
    setConfig((prev) => ({ ...prev, confidenceThreshold: value }));
  }, []);

  const setConfigFlag = useCallback(
    (key: 'includeIndividualPredictions' | 'includeRuntimeStatistics' | 'saveHistory' | 'generateReport', value: boolean) => {
      setConfig((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  return {
    uploadState,
    imageMeta,
    validationError,
    isAnalyzing,
    analyzeSteps,
    config,
    result,
    predictionError,
    onDrop,
    onDragEnter,
    onDragLeave,
    removeImage,
    analyze,
    setConfidenceThreshold,
    setConfigFlag,
  };
}
