import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Cpu, Layers, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { getClassLabelColor } from '@/constants/app';
import type { ApiError, PredictionResponse } from '@/types';

interface PredictionResultCardProps {
  result: PredictionResponse | null;
  error: ApiError | null;
  onReset: () => void;
  className?: string;
}

export function PredictionResultCard({ result, error, onReset, className }: PredictionResultCardProps) {

  if (!result && !error) return null;

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn('rounded-xl border border-destructive/30 bg-destructive/5 p-6', className)}
      >
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold">No prediction available</h3>
            <p className="text-sm text-muted-foreground">{error.message}</p>
            {error.requestId && (
              <p className="text-[11px] font-mono text-muted-foreground/70">Request ID: {error.requestId}</p>
            )}
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={onReset} className="mt-4 gap-1.5">
          <RotateCcw className="h-3.5 w-3.5" />
          Try again
        </Button>
      </motion.div>
    );
  }

  if (!result) return null;

  const { status, result: outcome, individual_predictions, runtime_statistics, metadata } = result;

  // IMPORTANT: verified directly against app/api/v1/predictions/router.py —
  // in the CURRENT backend code, PredictionStatus.SUCCESS and .FAILED are
  // never actually constructed anywhere in this response path. Only
  // PARTIAL_SUCCESS (≥1 model executed) or PENDING (engine stage skipped)
  // are ever returned today, regardless of how many models succeeded or
  // whether a full ensemble decision was reached. So `status` alone is NOT
  // a reliable signal of whether this is a "good" or "degraded" result —
  // that has to come from the actual data: whether `result` exists and how
  // many models succeeded/failed within it.
  const hasResult = Boolean(outcome) && outcome!.participating_models > 0;

  if (status === 'failed' || !hasResult) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn('rounded-xl border border-destructive/30 bg-destructive/5 p-6', className)}
      >
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold">No prediction available</h3>
            <p className="text-sm text-muted-foreground">
              {status === 'pending'
                ? "The prediction pipeline hasn't finished running for this request."
                : result.message}
            </p>
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={onReset} className="mt-4 gap-1.5">
          <RotateCcw className="h-3.5 w-3.5" />
          Try again
        </Button>
      </motion.div>
    );
  }

  // Real, meaningful partial-ness: some models that were part of this
  // request's run didn't produce a usable result. This is informational,
  // not alarming — the agreement/confidence figures above are still fully
  // valid for however many models did succeed.
  const hasFailedModels = outcome!.failed_models.length > 0;
  const labelColor = getClassLabelColor(outcome!.prediction);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('space-y-4', className)}
    >
      {hasFailedModels && (
        <div className="flex items-start gap-2.5 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
          <p className="text-xs text-amber-800 dark:text-amber-300">
            {outcome!.failed_models.length} model{outcome!.failed_models.length > 1 ? 's' : ''} failed to
            produce a result. The figures below reflect the {outcome!.successful_models.length} model
            {outcome!.successful_models.length > 1 ? 's' : ''} that did succeed.
          </p>
        </div>
      )}

      {/* Final result */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
          AI Prediction
        </div>
        <div className="mt-2 flex flex-wrap items-baseline gap-3">
          <span className="text-2xl font-bold font-display" style={{ color: labelColor }}>
            {outcome!.prediction}
          </span>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Metric label="Model Confidence" value={`${outcome!.confidence}%`} />
          <Metric label="Model Agreement" value={formatAgreement(outcome!.agreement_ratio)} />
          <Metric label="Participating Models" value={String(outcome!.participating_models)} />
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {outcome!.successful_models.map((m) => (
            <Badge key={m} variant="success">
              {m}
            </Badge>
          ))}
          {outcome!.failed_models.map((m) => (
            <Badge key={m} variant="destructive">
              {m} failed
            </Badge>
          ))}
        </div>
      </div>

      {/* Individual model predictions */}
      {individual_predictions && individual_predictions.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-6">
          <div className="mb-3 flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            <Layers className="h-3.5 w-3.5" />
            Individual Model Predictions
          </div>
          <div className="space-y-2">
            {individual_predictions.map((m) => (
              <div
                key={m.model_name}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-secondary/30 px-3 py-2 text-sm"
              >
                <span className="font-medium">{m.model_name}</span>
                <span className="text-muted-foreground">{m.prediction}</span>
                <span className="font-mono text-xs">{m.confidence}%</span>
                <span className="font-mono text-xs text-muted-foreground">{m.inference_time_ms} ms</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Runtime statistics */}
      {runtime_statistics && (
        <div className="rounded-xl border border-border bg-card p-6">
          <div className="mb-3 flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            <Cpu className="h-3.5 w-3.5" />
            Runtime Statistics
            <Badge variant={runtime_statistics.runtime_status === 'operational' ? 'success' : 'warning'}>
              {runtime_statistics.runtime_status}
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
            <Metric label="Loaded Models" value={String(runtime_statistics.loaded_model_count ?? '—')} small />
            <Metric
              label="Preprocessing"
              value={fmtMs(runtime_statistics.preprocessing_time_ms)}
              small
            />
            <Metric
              label="Total Inference"
              value={fmtMs(runtime_statistics.total_inference_time_ms)}
              small
            />
            <Metric
              label="Overall Time"
              value={fmtMs(runtime_statistics.overall_processing_time_ms)}
              small
            />
          </div>
        </div>
      )}

      {/* Metadata footer */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-1 text-[11px] font-mono text-muted-foreground/70">
        <span>API {metadata.api_version}</span>
        <span>Backend {metadata.backend_version}</span>
        {metadata.model_manifest_version && <span>Manifest {metadata.model_manifest_version}</span>}
        <span>{metadata.processing_time_ms} ms total</span>
      </div>

      <Button size="sm" variant="outline" onClick={onReset} className="gap-1.5">
        <RotateCcw className="h-3.5 w-3.5" />
        Analyze another image
      </Button>
    </motion.div>
  );
}

function Metric({ label, value, small = false, muted = false }: { label: string; value: string; small?: boolean; muted?: boolean }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={cn(small ? 'text-sm font-semibold' : 'text-lg font-bold font-display', muted && 'text-muted-foreground')}>
        {value}
      </p>
    </div>
  );
}

function fmtMs(value: number | null): string {
  return value === null ? '—' : `${value} ms`;
}

// Defensive against the value ever coming back null/undefined/NaN — shows
// a readable "N/A" instead of silently rendering blank or "NaN%". There is
// no longer a status-based special case here: verified against the real
// backend, agreement_ratio is a fully valid, meaningful number whenever
// `result` is present, regardless of whether status is partial_success.
function formatAgreement(agreementRatio: number | null | undefined): string {
  if (agreementRatio === null || agreementRatio === undefined || Number.isNaN(agreementRatio)) {
    return 'N/A';
  }
  return `${Math.round(agreementRatio * 100)}%`;
}
