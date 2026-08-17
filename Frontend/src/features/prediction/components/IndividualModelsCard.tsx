import { motion } from 'framer-motion';
import { Cpu, CheckCircle2, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { IndividualPrediction } from '@/types';

interface Props {
  models: IndividualPrediction[];
  className?: string;
}

function ConfidencePip({ value }: { value: number }) {
  const color =
    value >= 80 ? 'bg-emerald-500' : value >= 60 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div className="relative h-1 w-16 rounded-full bg-secondary overflow-hidden">
      <motion.div
        className={cn('h-full rounded-full', color)}
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(100, value)}%` }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      />
    </div>
  );
}

export function IndividualModelsCard({ models, className }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className={cn('rounded-xl border border-border bg-card p-5', className)}
    >
      <div className="flex items-center gap-2 mb-4">
        <Cpu className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold tracking-tight">Individual Model Breakdown</h3>
        <span className="ml-auto text-[11px] text-muted-foreground">{models.length} model{models.length !== 1 ? 's' : ''}</span>
      </div>

      <div className="space-y-1" role="table" aria-label="Individual model predictions">
        {/* Header */}
        <div
          className="grid grid-cols-[1fr_auto_auto_auto] gap-3 px-2 pb-1 text-[10px] uppercase tracking-widest text-muted-foreground/50"
          role="row"
        >
          <span role="columnheader">Model</span>
          <span role="columnheader" className="text-right">Class</span>
          <span role="columnheader" className="text-right">Confidence</span>
          <span role="columnheader" className="text-right">Time</span>
        </div>

        {models.map((m, idx) => (
          <motion.div
            key={m.model_name}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.05 * idx }}
            className="grid grid-cols-[1fr_auto_auto_auto] gap-3 items-center rounded-md px-2 py-2.5 hover:bg-secondary/60 transition-colors"
            role="row"
          >
            <div className="flex items-center gap-1.5 min-w-0" role="cell">
              <CheckCircle2 className="h-3 w-3 shrink-0 text-emerald-400" aria-hidden />
              <span className="text-xs font-medium truncate">{m.model_name}</span>
            </div>
            <span className="text-xs text-muted-foreground text-right font-mono" role="cell">
              {m.prediction}
            </span>
            <div className="flex items-center gap-2 justify-end" role="cell">
              <ConfidencePip value={m.confidence} />
              <span className="font-mono text-xs w-12 text-right">{m.confidence.toFixed(1)}%</span>
            </div>
            <span className="font-mono text-[11px] text-muted-foreground text-right" role="cell">
              {m.inference_time_ms.toFixed(0)}ms
            </span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

export function FailedModelsNote({ names }: { names: string[] }) {
  if (names.length === 0) return null;
  return (
    <div className="flex items-start gap-2 rounded-md border border-destructive/25 bg-destructive/5 px-3 py-2.5">
      <XCircle className="h-3.5 w-3.5 text-destructive shrink-0 mt-0.5" />
      <div>
        <p className="text-xs font-medium text-destructive">
          {names.length} model{names.length !== 1 ? 's' : ''} did not return a result
        </p>
        <p className="text-[11px] text-muted-foreground mt-0.5">{names.join(', ')}</p>
      </div>
    </div>
  );
}
