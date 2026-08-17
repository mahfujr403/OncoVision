import { Link } from 'react-router-dom';
import { History, BookOpen, RotateCcw, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { ROUTES } from '@/constants/routes';
import { usePredictionUpload } from '@/features/prediction/hooks/usePredictionUpload';
import { UploadCard } from '@/features/prediction/components/UploadCard';
import { PredictionSettingsCard } from '@/features/prediction/components/PredictionSettingsCard';
import { AnalyzeButton } from '@/features/prediction/components/AnalyzeButton';
import { UploadProgress } from '@/features/prediction/components/UploadProgress';
import { PredictionWorkflowCard } from '@/features/prediction/components/PredictionWorkflowCard';
import { PredictionInfoCard } from '@/features/prediction/components/PredictionInfoCard';
import { PredictionResultCard } from '@/features/prediction/components/PredictionResultCard';
import { IndividualModelsCard, FailedModelsNote } from '@/features/prediction/components/IndividualModelsCard';
import { RuntimeStatsCard } from '@/features/prediction/components/RuntimeStatsCard';

function errorTitle(statusCode?: number): string {
  switch (statusCode) {
    case 400: return 'Image rejected by server';
    case 422: return 'Invalid request parameters';
    case 503: return 'AI runtime unavailable';
    case 500: return 'Internal server error';
    default: return 'Submission failed';
  }
}

export default function PredictPage() {
  const {
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
  } = usePredictionUpload();

  const hasResult = predictionResult !== null;
  const hasError = predictionError !== null && !isAnalyzing;

  const workspaceStatus = hasResult
    ? 'complete'
    : hasError
      ? 'error'
      : isAnalyzing
        ? 'processing'
        : imageMeta
          ? 'uploading'
          : 'idle';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-6"
    >
      {/* Page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <SectionTitle
          title="New Prediction"
          description="Upload a histopathology slide image for AI-powered ensemble cancer classification."
        />
        <div className="flex shrink-0 items-center gap-2">
          {hasResult && (
            <Button variant="outline" size="sm" onClick={() => { resetResult(); removeImage(); }}>
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              New Analysis
            </Button>
          )}
          <Button asChild variant="ghost" size="sm">
            <Link to={ROUTES.HISTORY}>
              <History className="mr-1.5 h-3.5 w-3.5" />
              View History
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <a
              href="https://docs.oncovision.ai/prediction"
              target="_blank"
              rel="noopener noreferrer"
            >
              <BookOpen className="mr-1.5 h-3.5 w-3.5" />
              Documentation
            </a>
          </Button>
        </div>
      </div>

      {/* Two-column workspace */}
      <div className="grid gap-6 grid-cols-1 lg:grid-cols-[1fr_320px] xl:grid-cols-[1fr_360px]">

        {/* LEFT */}
        <div className="space-y-5">
          <AnimatePresence mode="wait">
            {hasResult ? (
              /* ── Result view ── */
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.35 }}
                className="space-y-5"
              >
                <PredictionResultCard prediction={predictionResult} />

                {predictionResult.individual_predictions &&
                  predictionResult.individual_predictions.length > 0 && (
                    <>
                      <IndividualModelsCard models={predictionResult.individual_predictions} />
                      {predictionResult.result?.failed_models &&
                        predictionResult.result.failed_models.length > 0 && (
                          <FailedModelsNote names={predictionResult.result.failed_models} />
                        )}
                    </>
                  )}

                {predictionResult.runtime_statistics && (
                  <RuntimeStatsCard
                    stats={predictionResult.runtime_statistics}
                    metadata={predictionResult.metadata}
                  />
                )}
              </motion.div>
            ) : (
              /* ── Upload view ── */
              <motion.div
                key="upload"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.35 }}
                className="space-y-5"
              >
                <UploadCard
                  uploadState={uploadState}
                  imageMeta={imageMeta}
                  validationError={validationError}
                  onDrop={onDrop}
                  onDragEnter={onDragEnter}
                  onDragLeave={onDragLeave}
                  onRemove={removeImage}
                />

                <PredictionSettingsCard
                  config={config}
                  onConfidenceChange={setConfidenceThreshold}
                />

                {/* Submission error */}
                {hasError && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/8 px-4 py-3"
                    role="alert"
                    aria-live="assertive"
                  >
                    <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-destructive leading-tight">
                        {errorTitle(predictionError.statusCode)}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                        {predictionError.message}
                      </p>
                    </div>
                  </motion.div>
                )}

                <UploadProgress steps={analyzeSteps} visible={isAnalyzing} />

                <AnalyzeButton
                  disabled={!imageMeta || uploadState === 'error'}
                  isAnalyzing={isAnalyzing}
                  onClick={analyze}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* RIGHT — sticky sidebar */}
        <aside className="lg:sticky lg:top-6 lg:self-start space-y-4">
          <PredictionWorkflowCard status={workspaceStatus} />
          <PredictionInfoCard />
        </aside>
      </div>
    </motion.div>
  );
}
