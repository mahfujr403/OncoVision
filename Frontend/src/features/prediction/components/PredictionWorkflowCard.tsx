import { motion } from 'framer-motion';
import { Upload, Cpu, GitMerge, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WORKFLOW_STEPS } from '../constants';
import type { WorkspaceStatus } from '../types';

const ICON_MAP: Record<string, React.ReactNode> = {
  upload: <Upload className="h-3.5 w-3.5" />,
  cpu: <Cpu className="h-3.5 w-3.5" />,
  'git-merge': <GitMerge className="h-3.5 w-3.5" />,
  'file-text': <FileText className="h-3.5 w-3.5" />,
};

function stepStatusFromWorkspace(
  step: number,
  workspaceStatus: WorkspaceStatus,
  analysisStage: number,
): 'done' | 'active' | 'pending' {
  if (workspaceStatus === 'complete') return 'done';
  if (workspaceStatus === 'error' || workspaceStatus === 'idle') return 'pending';

  if (workspaceStatus === 'uploading') {
    // Image selected but analysis not yet started.
    if (step === 1) return 'done';
    return 'pending';
  }

  // workspaceStatus === 'processing': step 1 (upload) is always done by
  // this point. Steps 2 and 3 progress one at a time via analysisStage,
  // which is staged locally in usePredictionUpload while the request is
  // in flight (the backend has no progress stream to drive this off of).
  if (step === 1) return 'done';
  if (step === 2) return analysisStage >= 2 ? 'done' : 'active';
  if (step === 3) return analysisStage >= 2 ? 'active' : 'pending';
  return 'pending';
}

interface PredictionWorkflowCardProps {
  status?: WorkspaceStatus;
  /** 0 = not analyzing, 1 = "AI Processing" active, 2 = "Ensemble Decision" active. */
  analysisStage?: number;
  className?: string;
}

export function PredictionWorkflowCard({
  status = 'idle',
  analysisStage = 0,
  className,
}: PredictionWorkflowCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.15 }}
      className={cn('rounded-lg border border-border bg-card p-4', className)}
    >
      <h3 className="mb-4 text-sm font-semibold tracking-tight">Analysis Workflow</h3>

      <ol className="relative space-y-0" aria-label="Analysis workflow steps">
        {WORKFLOW_STEPS.map((wf, idx) => {
          const stepStatus = stepStatusFromWorkspace(wf.step, status, analysisStage);
          const isLast = idx === WORKFLOW_STEPS.length - 1;

          return (
            <li key={wf.step} className="relative flex gap-3">
              {/* Connector line */}
              {!isLast && (
                <span
                  className={cn(
                    'absolute left-[13px] top-7 h-[calc(100%-4px)] w-px',
                    stepStatus === 'done' ? 'bg-primary/50' : 'bg-border',
                  )}
                  aria-hidden
                />
              )}

              {/* Step node */}
              <div
                className={cn(
                  'relative z-10 mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold transition-colors',
                  stepStatus === 'done' &&
                    'border-primary bg-primary/20 text-primary',
                  stepStatus === 'active' &&
                    'border-accent bg-accent/20 text-accent ring-2 ring-accent/30',
                  stepStatus === 'pending' &&
                    'border-border bg-background text-muted-foreground',
                )}
                aria-label={`Step ${wf.step}: ${stepStatus}`}
              >
                {stepStatus === 'active' ? (
                  <motion.span
                    animate={{ scale: [1, 1.15, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                  >
                    {ICON_MAP[wf.icon]}
                  </motion.span>
                ) : (
                  ICON_MAP[wf.icon]
                )}
              </div>

              {/* Step text */}
              <div className={cn('pb-5', isLast && 'pb-0')}>
                <p
                  className={cn(
                    'text-xs font-medium leading-5',
                    stepStatus === 'pending' && 'text-muted-foreground',
                    stepStatus === 'active' && 'text-accent',
                    stepStatus === 'done' && 'text-foreground',
                  )}
                >
                  {wf.label}
                </p>
                <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground/70">
                  {wf.description}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </motion.div>
  );
}