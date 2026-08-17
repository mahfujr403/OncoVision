import { motion } from 'framer-motion';
import {
  CheckCircle2, AlertTriangle, XCircle, Users, ShieldCheck, BarChart3,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';
import type { PredictionResponse, BackendPredictionStatus } from '@/types';

interface Props {
  prediction: PredictionResponse;
  className?: string;
}

function statusMeta(status: BackendPredictionStatus) {
  switch (status) {
    case 'success':
      return {
        icon: <CheckCircle2 className="h-5 w-5" />,
        label: 'AI Prediction Complete',
        color: 'text-emerald-400',
        ring: 'ring-emerald-500/30 bg-emerald-500/10',
        badge: 'success' as const,
      };
    case 'partial_success':
      return {
        icon: <AlertTriangle className="h-5 w-5" />,
        label: 'Partial Success',
        color: 'text-amber-400',
        ring: 'ring-amber-500/30 bg-amber-500/10',
        badge: 'warning' as const,
      };
    case 'failed':
      return {
        icon: <XCircle className="h-5 w-5" />,
        label: 'Prediction Failed',
        color: 'text-destructive',
        ring: 'ring-destructive/30 bg-destructive/10',
        badge: 'destructive' as const,
      };
    default:
      return {
        icon: <AlertTriangle className="h-5 w-5" />,
        label: 'Pending',
        color: 'text-muted-foreground',
        ring: 'ring-border bg-secondary',
        badge: 'default' as const,
      };
  }
}

function ConfidenceBar({ value }: { value: number }) {
  const clamped = Math.min(100, Math.max(0, value));
  const color =
    clamped >= 80 ? 'bg-emerald-500' : clamped >= 60 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div className="relative h-2 w-full rounded-full bg-secondary overflow-hidden">
      <motion.div
        className={cn('h-full rounded-full', color)}
        initial={{ width: 0 }}
        animate={{ width: `${clamped}%` }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
      />
    </div>
  );
}

export function PredictionResultCard({ prediction, className }: Props) {
  const meta = statusMeta(prediction.status);
  const { result } = prediction;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={cn('rounded-xl border border-border bg-card p-5 space-y-5', className)}
      role="region"
      aria-label="AI Prediction Result"
      aria-live="polite"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className={cn('flex h-9 w-9 items-center justify-center rounded-full ring-1', meta.ring, meta.color)}>
            {meta.icon}
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-tight">{meta.label}</h2>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              ID: <span className="font-mono">{prediction.prediction_id.slice(0, 8)}…</span>
            </p>
          </div>
        </div>
        <Badge variant={meta.badge} className="shrink-0 text-[10px]">
          {prediction.status.replace('_', ' ').toUpperCase()}
        </Badge>
      </div>

      {/* Result block — full success */}
      {result && (
        <div className="space-y-4">
          {/* Predicted class */}
          <div className="rounded-lg border border-border/60 bg-secondary/40 p-4">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground/60 mb-1">
              Predicted Class
            </p>
            <p className="text-xl font-bold tracking-tight leading-none">{result.prediction}</p>
            <p className="text-[11px] text-muted-foreground mt-1.5">
              AI-assisted analysis — not a clinical diagnosis
            </p>
          </div>

          {/* Confidence */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <BarChart3 className="h-3.5 w-3.5" />
                Model Confidence
              </span>
              <span className="font-mono font-semibold">{result.confidence.toFixed(1)}%</span>
            </div>
            <ConfidenceBar value={result.confidence} />
          </div>

          {/* Agreement */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <ShieldCheck className="h-3.5 w-3.5" />
                Model Agreement
              </span>
              <span className="font-mono font-semibold">
                {(result.agreement_ratio * 100).toFixed(0)}%
              </span>
            </div>
            <ConfidenceBar value={result.agreement_ratio * 100} />
          </div>

          {/* Model counts */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 rounded-md border border-border/50 bg-secondary/60 px-2.5 py-1.5">
              <Users className="h-3 w-3 text-muted-foreground" />
              <span className="text-[11px] text-muted-foreground">
                {result.successful_models.length}/{result.participating_models} models succeeded
              </span>
            </div>
            {result.failed_models.length > 0 && (
              <div className="flex items-center gap-1.5 rounded-md border border-destructive/30 bg-destructive/10 px-2.5 py-1.5">
                <XCircle className="h-3 w-3 text-destructive" />
                <span className="text-[11px] text-destructive">
                  {result.failed_models.length} model{result.failed_models.length !== 1 ? 's' : ''} failed
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Partial success — individual predictions present but no ensemble result */}
      {!result && prediction.status === 'partial_success' && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 space-y-1">
          <p className="text-sm font-medium text-amber-400">No ensemble result produced</p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {prediction.message ||
              'Some models returned predictions but the ensemble did not reach consensus. See the individual model breakdown below.'}
          </p>
        </div>
      )}

      {/* Failed */}
      {prediction.status === 'failed' && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
          <p className="text-sm font-medium text-destructive">Prediction pipeline failed</p>
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
            {prediction.message}
          </p>
        </div>
      )}

      {/* Disclaimer */}
      <p className="text-[10px] text-muted-foreground/50 leading-relaxed border-t border-border/40 pt-3">
        This AI prediction is intended for research assistance only. It does not constitute a
        clinical diagnosis. Always confirm findings with a qualified pathologist.
      </p>
    </motion.div>
  );
}
