import { motion } from 'framer-motion';
import { Microscope, ArrowUp, Sparkles } from 'lucide-react';

export function PredictionEmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="flex flex-col items-center justify-center py-16 px-6 text-center"
      aria-live="polite"
      aria-label="No image selected"
    >
      {/* Illustration */}
      <div className="relative mb-6">
        {/* Outer ring */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          className="absolute -inset-4 rounded-full border border-dashed border-primary/20"
        />
        {/* Middle ring */}
        <motion.div
          animate={{ rotate: -360 }}
          transition={{ duration: 14, repeat: Infinity, ease: 'linear' }}
          className="absolute -inset-1 rounded-full border border-dashed border-primary/10"
        />

        {/* Centre icon */}
        <div className="relative flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-primary/20 to-accent/10 shadow-inner">
          <Microscope className="h-10 w-10 text-primary/70" strokeWidth={1.5} aria-hidden />

          {/* Orbiting sparkle */}
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
            className="absolute inset-0"
          >
            <div className="absolute -top-1.5 left-1/2 -translate-x-1/2">
              <Sparkles className="h-4 w-4 text-accent" />
            </div>
          </motion.div>
        </div>
      </div>

      {/* Text */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.35 }}
        className="space-y-2 max-w-xs"
      >
        <h3 className="text-base font-semibold tracking-tight">No Image Selected</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Upload a histopathology image to begin AI-powered cancer classification.
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
