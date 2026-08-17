import { useState, useCallback, useEffect, useRef } from 'react';
import type { FileRejection } from 'react-dropzone';
import { ACCEPTED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES, MAX_IMAGE_SIZE_MB } from '@/constants/app';
import type { NormalisedApiError } from '@/api/interceptors';
import type {
  ImageMeta,
  ValidationError,
  UploadState,
  PredictionConfig,
  AnalyzeStepInfo,
} from '../types';
import type { PredictionResponse } from '@/types';
import { useCreatePrediction } from './usePredictionQuery';

const ACCEPTED_MIME_TYPES = Object.keys(ACCEPTED_IMAGE_TYPES) as string[];

function getExtension(mimeType: string): string {
  const map: Record<string, string> = {
    'image/jpeg': 'JPG',
    'image/png': 'PNG',
    'image/tiff': 'TIFF',
    'image/bmp': 'BMP',
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
  confidenceThreshold: 0.75,
  // These three are static UI labels only — not sent to the backend
  ensembleMethod: 'Weighted Voting',
  imageSize: '— × — px',
  modelVersion: 'v3.0.1',
};

export interface PredictionSubmitError {
  message: string;
  statusCode?: number;
}

function classifyError(err: unknown): PredictionSubmitError {
  const apiErr = err as Partial<NormalisedApiError>;
  const message = apiErr.message ?? 'An unexpected error occurred. Please try again.';
  return { message, statusCode: apiErr.statusCode };
}

export function usePredictionUpload() {
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [imageMeta, setImageMeta] = useState<ImageMeta | null>(null);
  const [validationError, setValidationError] = useState<ValidationError | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeSteps, setAnalyzeSteps] = useState<AnalyzeStepInfo[]>(INITIAL_STEPS);
  const [config, setConfig] = useState<PredictionConfig>(DEFAULT_CONFIG);
  const [predictionResult, setPredictionResult] = useState<PredictionResponse | null>(null);
  const [predictionError, setPredictionError] = useState<PredictionSubmitError | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  const mutation = useCreatePrediction();

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
    setConfig((prev) => ({
      ...prev,
      imageSize: width && height ? `${width} × ${height} px` : '— × — px',
    }));
  }, []);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejections: FileRejection[]) => {
      setUploadState('idle');
      if (rejections.length > 0) {
        const first = rejections[0].errors[0];
        const code =
          first.code === 'file-too-large'
            ? 'size'
            : first.code === 'file-invalid-type'
              ? 'type'
              : 'unknown';
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
    setPredictionResult(null);
    setPredictionError(null);
  }, []);

  const resetResult = useCallback(() => {
    setPredictionResult(null);
    setPredictionError(null);
    setAnalyzeSteps(INITIAL_STEPS);
  }, []);

  const setStepStatus = (
    id: AnalyzeStepInfo['id'],
    status: AnalyzeStepInfo['status'],
  ) => {
    setAnalyzeSteps((steps) => steps.map((s) => (s.id === id ? { ...s, status } : s)));
  };

  const analyze = useCallback(async () => {
    if (!imageMeta || isAnalyzing || mutation.isPending) return;

    setIsAnalyzing(true);
    setAnalyzeSteps(INITIAL_STEPS);
    setPredictionResult(null);
    setPredictionError(null);

    // Step 1 active: file about to be sent
    setAnalyzeSteps((s) => s.map((step) => (step.id === 'upload' ? { ...step, status: 'active' } : step)));

    let uploadFinished = false;

    const onUploadDone = () => {
      if (uploadFinished) return;
      uploadFinished = true;
      setAnalyzeSteps((s) =>
        s.map((step) => {
          if (step.id === 'upload') return { ...step, status: 'done' };
          if (step.id === 'prepare') return { ...step, status: 'done' };
          if (step.id === 'request') return { ...step, status: 'done' };
          if (step.id === 'waiting') return { ...step, status: 'active' };
          return step;
        }),
      );
    };

    try {
      const result = await mutation.mutateAsync({
        image: imageMeta.file,
        options: {
          confidence_threshold: config.confidenceThreshold,
          include_individual_predictions: true,
          include_runtime_statistics: true,
          save_history: true,
        },
        onUploadProgress: (pct) => {
          if (pct >= 100) onUploadDone();
        },
      });

      // Ensure steps finished even if onUploadProgress never fired at 100
      onUploadDone();

      setAnalyzeSteps(INITIAL_STEPS.map((s) => ({ ...s, status: 'done' as const })));
      setPredictionResult(result);
    } catch (err) {
      onUploadDone();
      setAnalyzeSteps((s) =>
        s.map((step) =>
          step.status === 'active' || step.status === 'pending'
            ? { ...step, status: step.status === 'active' ? 'error' : step.status }
            : step,
        ),
      );
      setPredictionError(classifyError(err));
    } finally {
      setIsAnalyzing(false);
    }
  }, [imageMeta, isAnalyzing, config, mutation]);

  const setConfidenceThreshold = useCallback((value: number) => {
    setConfig((prev) => ({ ...prev, confidenceThreshold: value }));
  }, []);

  return {
    uploadState,
    imageMeta,
    validationError,
    isAnalyzing,
    analyzeSteps,
    config,
    predictionResult,
    predictionError,
    onDrop,
    onDragEnter,
    onDragLeave,
    removeImage,
    resetResult,
    analyze,
    setConfidenceThreshold,
    setStepStatus,
  };
}
