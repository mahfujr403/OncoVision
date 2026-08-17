import { motion } from 'framer-motion';
import { FileImage, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SUPPORTED_FORMATS, IMAGE_REQUIREMENTS } from '../constants';

interface PredictionInfoCardProps {
  className?: string;
}

export function PredictionInfoCard({ className }: PredictionInfoCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.1 }}
      className={cn('space-y-3', className)}
    >
      {/* Supported Formats */}
      <div className="rounded-lg border border-border bg-card p-4">
        <div className="mb-3 flex items-center gap-2">
          <FileImage className="h-4 w-4 text-primary" aria-hidden />
          <h3 className="text-sm font-semibold tracking-tight">Supported Formats</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {SUPPORTED_FORMATS.filter(
            (f, i, arr) => arr.findIndex((x) => x.ext === f.ext) === i,
          ).map((fmt) => (
            <span
              key={fmt.ext}
              className="rounded-md border border-primary/20 bg-primary/5 px-2.5 py-1 font-mono text-xs font-medium text-primary"
            >
              .{fmt.ext}
            </span>
          ))}
        </div>
      </div>

      {/* Image Requirements */}
      <div className="rounded-lg border border-border bg-card p-4">
        <div className="mb-3 flex items-center gap-2">
          <Info className="h-4 w-4 text-accent" aria-hidden />
          <h3 className="text-sm font-semibold tracking-tight">Image Requirements</h3>
        </div>
        <ul className="space-y-2">
          {IMAGE_REQUIREMENTS.map((req) => (
            <li key={req.label} className="flex items-center justify-between gap-2">
              <span className="text-xs text-muted-foreground">{req.label}</span>
              <span className="text-xs font-medium tabular-nums">{req.value}</span>
            </li>
          ))}
        </ul>
      </div>
    </motion.div>
  );
}
