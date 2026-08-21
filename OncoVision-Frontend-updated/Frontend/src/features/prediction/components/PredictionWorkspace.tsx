import { cn } from '@/lib/utils';
import { PredictionEmptyState } from './PredictionEmptyState';
import { PredictionStatusCard } from './PredictionStatusCard';
import type { WorkspaceStatus } from '../types';

interface PredictionWorkspaceProps {
  status?: WorkspaceStatus;
  className?: string;
}

export function PredictionWorkspace({ status = 'idle', className }: PredictionWorkspaceProps) {
  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* ── Upload zone (placeholder) ── */}
      <section
        className="flex min-h-[340px] flex-col items-stretch rounded-xl border-2 border-dashed border-border/60 bg-card/40 backdrop-blur-sm transition-colors hover:border-primary/30 hover:bg-card/60"
        aria-label="Image upload area"
      >
        <PredictionEmptyState />
      </section>

      {/* ── Model configuration (placeholder) ── */}
      <section
        className="rounded-xl border border-border bg-card p-5"
        aria-label="Model configuration"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-tight">Model Configuration</h2>
          <span className="rounded-full border border-border bg-background px-2.5 py-0.5 text-[10px] font-medium text-muted-foreground">
            6 models active
          </span>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          The ensemble configuration panel will appear here once an image is loaded. You will be able
          to toggle individual models, adjust confidence thresholds, and choose the cancer type to
          analyse.
        </p>
      </section>

      {/* ── Live status ── */}
      <PredictionStatusCard status={status} />
    </div>
  );
}
