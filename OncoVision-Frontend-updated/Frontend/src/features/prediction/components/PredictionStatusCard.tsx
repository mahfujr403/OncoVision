import { motion } from 'framer-motion';
import { Clock, CheckCircle2, AlertCircle, Loader2, Upload } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkspaceStatus } from '../types';

interface StatusConfig {
  icon: React.ReactNode;
  label: string;
  description: string;
  color: string;
  animate: boolean;
}

const STATUS_CONFIG: Record<WorkspaceStatus, StatusConfig> = {
  idle: {
    icon: <Clock className="h-4 w-4" />,
    label: 'Waiting for image upload…',
    description: 'Select a histopathology slide to begin.',
    color: 'text-muted-foreground',
    animate: true,
  },
  uploading: {
    icon: <Upload className="h-4 w-4" />,
    label: 'Uploading image…',
    description: 'Transferring your slide to the analysis pipeline.',
    color: 'text-primary',
    animate: true,
  },
  processing: {
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    label: 'Ensemble AI processing…',
    description: 'Six models are running in parallel.',
    color: 'text-accent',
    animate: false,
  },
  complete: {
    icon: <CheckCircle2 className="h-4 w-4" />,
    label: 'Classification complete',
    description: 'Results are ready to review.',
    color: 'text-emerald-400',
    animate: false,
  },
  error: {
    icon: <AlertCircle className="h-4 w-4" />,
    label: 'Analysis failed',
    description: 'An error occurred. Please try again.',
    color: 'text-destructive',
    animate: false,
  },
};

interface PredictionStatusCardProps {
  status?: WorkspaceStatus;
  className?: string;
}

export function PredictionStatusCard({ status = 'idle', className }: PredictionStatusCardProps) {
  const config = STATUS_CONFIG[status];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        'flex items-start gap-3 rounded-lg border border-border bg-card p-4',
        className,
      )}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {/* Status dot + icon */}
      <div className={cn('mt-0.5 shrink-0', config.color)}>
        <div className="relative">
          {config.animate && (
            <motion.span
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
              className={cn(
                'absolute -inset-1.5 rounded-full',
                status === 'idle' ? 'bg-muted-foreground/10' : 'bg-primary/10',
              )}
            />
          )}
          {config.icon}
        </div>
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0">
        <p className={cn('text-sm font-medium', config.color)}>{config.label}</p>
        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{config.description}</p>
      </div>

      {/* Processing progress dots */}
      {status === 'processing' && (
        <div className="flex items-center gap-1 shrink-0 mt-0.5">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2, ease: 'easeInOut' }}
              className="h-1.5 w-1.5 rounded-full bg-accent"
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
