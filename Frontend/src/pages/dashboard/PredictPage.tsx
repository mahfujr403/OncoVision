import { Link } from 'react-router-dom';
import { History, BookOpen } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { ROUTES } from '@/constants/routes';
import { usePredictionUpload } from '@/features/prediction/hooks/usePredictionUpload';
import { UploadCard } from '@/features/prediction/components/UploadCard';
import { PredictionSettingsCard } from '@/features/prediction/components/PredictionSettingsCard';
import { AnalyzeButton } from '@/features/prediction/components/AnalyzeButton';
import { UploadProgress } from '@/features/prediction/components/UploadProgress';
import { PredictionResultCard } from '@/features/prediction/components/PredictionResultCard';
import { PredictionWorkflowCard } from '@/features/prediction/components/PredictionWorkflowCard';
import { PredictionInfoCard } from '@/features/prediction/components/PredictionInfoCard';

export default function PredictPage() {
  const {
    uploadState,
    imageMeta,
    validationError,
    isAnalyzing,
    analyzeSteps,
    analysisStage,
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
  } = usePredictionUpload();

  const workspaceStatus = predictionError
    ? 'error'
    : result
      ? 'complete'
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
      {/* ── Page header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <SectionTitle
          title="New Prediction"
          description="Upload a histopathology slide image for AI-powered ensemble cancer classification."
        />
        <div className="flex shrink-0 items-center gap-2">
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

      {/* ── Two-column workspace ── */}
      <div className="grid gap-6 grid-cols-1 lg:grid-cols-[1fr_320px] xl:grid-cols-[1fr_360px]">

        {/* LEFT — upload + settings + submit */}
        <div className="space-y-5">
          {/* Upload */}
          <UploadCard
            uploadState={uploadState}
            imageMeta={imageMeta}
            validationError={validationError}
            onDrop={onDrop}
            onDragEnter={onDragEnter}
            onDragLeave={onDragLeave}
            onRemove={removeImage}
          />

          {/* Settings */}
          <PredictionSettingsCard
            config={config}
            onConfidenceChange={setConfidenceThreshold}
            onFlagChange={setConfigFlag}
          />

          {/* Progress (shown while analyzing) */}
          <UploadProgress steps={analyzeSteps} visible={isAnalyzing} />

          {/* Analyze */}
          <AnalyzeButton
            disabled={!imageMeta || uploadState === 'error'}
            isAnalyzing={isAnalyzing}
            onClick={analyze}
          />

          {/* Real prediction result / error */}
          <PredictionResultCard result={result} error={predictionError} onReset={removeImage} />
        </div>

        {/* RIGHT — sticky sidebar */}
        <aside className="lg:sticky lg:top-6 lg:self-start space-y-4">
          <PredictionWorkflowCard status={workspaceStatus} analysisStage={analysisStage} />
          <PredictionInfoCard />
        </aside>
      </div>
    </motion.div>
  );
}