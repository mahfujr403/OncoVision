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

  if (status === 'failed' || !outcome) {
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
            <p className="text-sm text-muted-foreground">{result.message}</p>
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={onReset} className="mt-4 gap-1.5">
          <RotateCcw className="h-3.5 w-3.5" />
          Try again
        </Button>
      </motion.div>
    );
  }

  const isPartial = status === 'partial_success';
  const labelColor = getClassLabelColor(outcome.prediction);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('space-y-4', className)}
    >
      {isPartial && (
        <div className="flex items-start gap-2.5 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
          <p className="text-xs text-amber-800 dark:text-amber-300">
            Partial result — only one model completed. No ensemble agreement is available for this
            prediction.
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
            {outcome.prediction}
          </span>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Metric label="Model Confidence" value={`${outcome.confidence.toFixed(1)}%`} />
          <Metric
            label="Model Agreement"
            value={isPartial ? '—' : `${Math.round(outcome.agreement_ratio * 100)}%`}
            muted={isPartial}
          />
          <Metric label="Participating Models" value={String(outcome.participating_models)} />
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {outcome.successful_models.map((m) => (
            <Badge key={m} variant="success">
              {m}
            </Badge>
          ))}
          {outcome.failed_models.map((m) => (
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
                <span className="font-mono text-xs">{m.confidence.toFixed(1)}%</span>
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
