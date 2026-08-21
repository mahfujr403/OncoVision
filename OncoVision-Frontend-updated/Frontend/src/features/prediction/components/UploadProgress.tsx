import { motion, AnimatePresence } from 'framer-motion';
import { Check, Loader2, AlertCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AnalyzeStepInfo, StepStatus } from '../types';

function StepIcon({ status }: { status: StepStatus }) {
  if (status === 'done')
    return (
      <motion.span
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
        className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400"
      >
        <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
      </motion.span>
    );
  if (status === 'active')
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/20 text-primary">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      </span>
    );
  if (status === 'error')
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-destructive/20 text-destructive">
        <AlertCircle className="h-3.5 w-3.5" />
      </span>
    );
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full border border-border text-muted-foreground/50">
      <Clock className="h-3 w-3" />
    </span>
  );
}

interface UploadProgressProps {
  steps: AnalyzeStepInfo[];
  visible: boolean;
  className?: string;
}

export function UploadProgress({ steps, visible, className }: UploadProgressProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="upload-progress"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
          className={cn('overflow-hidden', className)}
        >
          <div className="rounded-xl border border-border bg-card/80 backdrop-blur-sm p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Analysis Progress
            </p>
            <ol className="relative space-y-0">
              {steps.map((step, idx) => {
                const isLast = idx === steps.length - 1;
                return (
                  <li key={step.id} className="relative flex gap-3">
                    {/* Connector */}
                    {!isLast && (
                      <span
                        className={cn(
                          'absolute left-[11px] top-6 h-[calc(100%-4px)] w-px transition-colors duration-500',
                          step.status === 'done' ? 'bg-emerald-500/40' : 'bg-border',
                        )}
                        aria-hidden
                      />
                    )}

                    {/* Icon */}
                    <div className="relative z-10 mt-0.5 shrink-0">
                      <StepIcon status={step.status} />
                    </div>

                    {/* Label */}
                    <div className={cn('pb-4', isLast && 'pb-0')}>
                      <p
                        className={cn(
                          'text-sm font-medium leading-6 transition-colors duration-300',
                          step.status === 'done' && 'text-emerald-400',
                          step.status === 'active' && 'text-primary',
                          step.status === 'error' && 'text-destructive',
                          step.status === 'pending' && 'text-muted-foreground',
                        )}
                      >
                        {step.status === 'active' && (
                          <motion.span
                            animate={{ opacity: [1, 0.5, 1] }}
                            transition={{ duration: 1.2, repeat: Infinity }}
                            className="inline-block"
                          >
                            ⏳{' '}
                          </motion.span>
                        )}
                        {step.status === 'done' && '✓ '}
                        {step.label}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
