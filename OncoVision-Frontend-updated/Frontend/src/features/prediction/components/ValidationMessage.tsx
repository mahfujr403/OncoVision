import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, XCircle, HardDrive, FileX, FileWarning } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ValidationError } from '../types';

const ICON_MAP: Record<ValidationError['code'], React.ReactNode> = {
  type: <FileWarning className="h-4 w-4 shrink-0" />,
  size: <HardDrive className="h-4 w-4 shrink-0" />,
  corrupt: <XCircle className="h-4 w-4 shrink-0" />,
  empty: <FileX className="h-4 w-4 shrink-0" />,
  unknown: <AlertTriangle className="h-4 w-4 shrink-0" />,
};

interface ValidationMessageProps {
  error: ValidationError | null;
  className?: string;
}

export function ValidationMessage({ error, className }: ValidationMessageProps) {
  return (
    <AnimatePresence mode="wait">
      {error && (
        <motion.div
          key={error.code + error.message}
          initial={{ opacity: 0, y: -4, height: 0 }}
          animate={{ opacity: 1, y: 0, height: 'auto' }}
          exit={{ opacity: 0, y: -4, height: 0 }}
          transition={{ duration: 0.22 }}
          className={cn('overflow-hidden', className)}
        >
          <div
            className="flex items-start gap-2.5 rounded-lg border border-destructive/30 bg-destructive/8 px-3.5 py-3 text-destructive"
            role="alert"
            aria-live="assertive"
          >
            {ICON_MAP[error.code]}
            <p className="text-xs leading-relaxed">{error.message}</p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
