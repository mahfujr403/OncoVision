import { motion } from 'framer-motion';
import { Settings2, FlaskConical } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PredictionConfig } from '../types';

interface PredictionSettingsCardProps {
  config: PredictionConfig;
  onConfidenceChange: (value: number) => void;
  onFlagChange: (
    key: 'includeIndividualPredictions' | 'includeRuntimeStatistics' | 'saveHistory' | 'generateReport',
    value: boolean,
  ) => void;
  className?: string;
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
  disabled = false,
  disabledNote,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
  disabledNote?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="space-y-0.5">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-foreground">{label}</span>
          {disabled && disabledNote && (
            <span className="rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-600 dark:text-amber-400">
              {disabledNote}
            </span>
          )}
        </div>
        <p className="text-[11px] leading-snug text-muted-foreground max-w-[220px]">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
          checked && !disabled ? 'bg-primary' : 'bg-secondary',
          disabled && 'cursor-not-allowed opacity-50',
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 h-4 w-4 rounded-full bg-background shadow transition-transform',
            checked ? 'translate-x-4' : 'translate-x-0.5',
          )}
        />
      </button>
    </div>
  );
}

export function PredictionSettingsCard({
  config,
  onConfidenceChange,
  onFlagChange,
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
      <div className="mb-4 flex items-center gap-2">
        <Settings2 className="h-4 w-4 text-primary" aria-hidden />
        <h2 className="text-sm font-semibold tracking-tight">Prediction Settings</h2>
      </div>

      <div className="space-y-4">
        {/* Confidence threshold slider */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Reliability Threshold</span>
            <span className="font-mono text-xs font-semibold text-primary">{pct}%</span>
          </div>
          <div className="relative">
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={pct}
              onChange={(e) => onConfidenceChange(Number(e.target.value) / 100)}
              aria-label={`Reliability threshold: ${pct}%`}
              className="w-full cursor-pointer appearance-none rounded-full bg-secondary h-1.5 accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
            />
            <div
              className="pointer-events-none absolute left-0 top-0 h-1.5 rounded-full bg-primary/70 mt-0"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-[11px] leading-snug text-muted-foreground">
            Used only to flag low-reliability results for review — it never changes what the models
            predict.
          </p>
        </div>

        <hr className="border-border/50" />

        <ToggleRow
          label="Individual model predictions"
          description="Include each model's own prediction alongside the final ensemble result."
          checked={config.includeIndividualPredictions}
          onChange={(v) => onFlagChange('includeIndividualPredictions', v)}
        />

        <ToggleRow
          label="Runtime statistics"
          description="Include AI runtime health and execution timing in the response."
          checked={config.includeRuntimeStatistics}
          onChange={(v) => onFlagChange('includeRuntimeStatistics', v)}
        />

        <ToggleRow
          label="Save to history"
          description="Persist this prediction to your Prediction History."
          checked={config.saveHistory}
          onChange={(v) => onFlagChange('saveHistory', v)}
        />

        <ToggleRow
          label="Generate report"
          description="Accepted by the API today, but report generation isn't implemented on this endpoint yet."
          checked={config.generateReport}
          onChange={(v) => onFlagChange('generateReport', v)}
          disabled
          disabledNote="Coming soon"
        />

        {config.imageSize !== '— × — px' && (
          <>
            <hr className="border-border/50" />
            <div className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <FlaskConical className="h-3 w-3" />
                Image dimensions
              </span>
              <span className="rounded-md border border-border/50 bg-secondary/60 px-2.5 py-1 font-mono text-xs">
                {config.imageSize}
              </span>
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
}
