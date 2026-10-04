import { motion } from 'framer-motion';
import { Microscope, ArrowUp } from 'lucide-react';

export function PredictionEmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="flex flex-col items-center justify-center py-16 px-6 text-center"
      aria-live="polite"
      aria-label="No specimen image selected"
    >
      {/* Reticle / Focal Point */}
      <div className="relative mb-6">
        <div className="absolute -inset-3 rounded-full border border-border-subtle" />
        <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-surface-raised border border-border">
          <Microscope className="h-9 w-9 text-primary/80" strokeWidth={1.5} aria-hidden="true" />
        </div>
      </div>

      {/* Text */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.35 }}
        className="space-y-2 max-w-xs"
      >
        <h3 className="text-base font-semibold tracking-tight">No Specimen Selected</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Upload a histopathology slide image to initiate deep learning ensemble classification.
        </p>
      </motion.div>

      {/* Upload cue */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.28, duration: 0.35 }}
        className="mt-6 flex items-center gap-1.5 text-xs text-muted-foreground/60"
      >
        <ArrowUp className="h-3 w-3" />
        Drop your slide image above to get started
      </motion.div>
    </motion.div>
  );
}
