import { useState } from 'react';
import { ScanLine } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { UploadZone } from '@/components/predict/UploadZone';
import { PredictionOptionsPanel } from '@/components/predict/PredictionOptionsPanel';
import { ProcessingPanel } from '@/components/predict/ProcessingPanel';
import { PredictionResultView, PredictionErrorView } from '@/components/predict/PredictionResultView';
import { simulatePredictionRequest } from '@/lib/mockPrediction';
import { DEFAULT_PREDICTION_OPTIONS, type PredictionRequestOptions, type PredictionResponse } from '@/types/prediction';

type WorkflowState = 'idle' | 'processing' | 'result' | 'error';

export function PredictPage() {
  const [file, setFile] = useState<File | null>(null);
  const [options, setOptions] = useState<PredictionRequestOptions>(DEFAULT_PREDICTION_OPTIONS);
  const [state, setState] = useState<WorkflowState>('idle');
  const [response, setResponse] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<unknown>(null);

  function reset() {
    setFile(null);
    setResponse(null);
    setError(null);
    setState('idle');
  }

  async function handleAnalyze() {
    if (!file) return;
    setState('processing');
    setError(null);
    try {
      const result = await simulatePredictionRequest(file, options);
      setResponse(result);
      setState('result');
    } catch (err) {
      setError(err);
      setState('error');
    }
  }

  const showForm = state === 'idle';

  return (
    <div className="p-6 max-w-[1000px] mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
              <ScanLine className="w-4.5 h-4.5" />
            </div>
            <h1 className="text-xl font-bold text-foreground">Prediction Workspace</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1.5 ml-[46px]">
            Upload a histopathology image to run AI-assisted classification.
          </p>
        </div>
      </div>

      {showForm && (
        <>
          <UploadZone file={file} onFileSelected={setFile} onClear={reset} />
          <PredictionOptionsPanel options={options} onChange={setOptions} />
          <div className="flex justify-end">
            <Button variant="primary" size="lg" disabled={!file} onClick={handleAnalyze}>
              Analyze Image
            </Button>
          </div>
        </>
      )}

      {state === 'processing' && file && <ProcessingPanel fileName={file.name} />}

      {state === 'result' && response && (
        <PredictionResultView response={response} onStartNew={reset} />
      )}

      {state === 'error' && <PredictionErrorView error={error} onRetry={reset} />}

    </div>
  );
}

export default PredictPage;
