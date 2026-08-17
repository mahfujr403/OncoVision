import { motion } from 'framer-motion';
import { Settings2, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PredictionConfig } from '../types';

interface PredictionSettingsCardProps {
  config: PredictionConfig;
  onConfidenceChange: (value: number) => void;
  className?: string;
}

function ReadOnlyField({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span
        className={cn(
          'rounded-md border border-border/50 bg-secondary/60 px-2.5 py-1 text-xs',
          mono && 'font-mono',
        )}
      >
        {value}
      </span>
    </div>
  );
}

export function PredictionSettingsCard({
  config,
  onConfidenceChange,
  className,
}: PredictionSettingsCardProps) {
  const pct = Math.round(config.confidenceThreshold * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.05 }}
      className={cn('rounded-xl border border-border bg-card p-5', className)}
    >
      {/* Header */}
      <div className="mb-4 flex items-center gap-2">
        <Settings2 className="h-4 w-4 text-primary" aria-hidden />
        <h2 className="text-sm font-semibold tracking-tight">Prediction Settings</h2>
      </div>

      <div className="space-y-4">
        {/* Ensemble method — disabled */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Ensemble Method</span>
            <span
              title="Locked for clinical use"
              className="cursor-help text-muted-foreground/40"
              aria-label="Locked for clinical use"
            >
              <Info className="h-3 w-3" />
            </span>
          </div>
          <span className="rounded-md border border-border/30 bg-secondary/30 px-2.5 py-1 font-mono text-xs text-muted-foreground/60 line-through decoration-dashed">
            {config.ensembleMethod}
          </span>
        </div>

        <ReadOnlyField label="Image Size" value={config.imageSize} mono />
        <ReadOnlyField label="Model Version" value={config.modelVersion} mono />

        {/* Divider */}
        <hr className="border-border/50" />

        {/* Confidence threshold slider */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Confidence Threshold</span>
            <span className="font-mono text-xs font-semibold text-primary">{pct}%</span>
          </div>
          <div className="relative">
            <input
              type="range"
              min={50}
              max={99}
              step={1}
              value={pct}
              onChange={(e) => onConfidenceChange(Number(e.target.value) / 100)}
              aria-label={`Confidence threshold: ${pct}%`}
              className="w-full cursor-pointer appearance-none rounded-full bg-secondary h-1.5 accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
            />
            {/* Track fill visual */}
            <div
              className="pointer-events-none absolute left-0 top-0 h-1.5 rounded-full bg-primary/70 mt-0"
              style={{ width: `${((pct - 50) / 49) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground/50">
            <span>50%</span>
            <span>75%</span>
            <span>99%</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
