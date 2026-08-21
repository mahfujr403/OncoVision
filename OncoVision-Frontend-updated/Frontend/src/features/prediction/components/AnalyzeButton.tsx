import { motion } from 'framer-motion';
import { Microscope, Loader2, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AnalyzeButtonProps {
  disabled: boolean;
  isAnalyzing: boolean;
  onClick: () => void;
  className?: string;
}

export function AnalyzeButton({ disabled, isAnalyzing, onClick, className }: AnalyzeButtonProps) {
  const isReady = !disabled && !isAnalyzing;

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled || isAnalyzing}
      whileTap={isReady ? { scale: 0.97 } : {}}
      whileHover={isReady ? { scale: 1.01 } : {}}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      aria-label={isAnalyzing ? 'Analysis in progress…' : 'Run AI prediction'}
      aria-busy={isAnalyzing}
      className={cn(
        'relative flex w-full items-center justify-center gap-2.5 overflow-hidden rounded-xl px-6 py-3.5 text-sm font-semibold tracking-wide transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        isReady
          ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/25 hover:shadow-primary/40 hover:opacity-95'
          : isAnalyzing
            ? 'bg-primary/80 text-primary-foreground cursor-wait'
            : 'bg-secondary text-muted-foreground cursor-not-allowed',
        className,
      )}
    >
      {/* Animated shimmer on ready state */}
      {isReady && (
        <motion.div
          animate={{ x: ['-100%', '200%'] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut', repeatDelay: 1 }}
          className="pointer-events-none absolute inset-0 -skew-x-12 bg-gradient-to-r from-transparent via-white/10 to-transparent"
        />
      )}

      {isAnalyzing ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Analyzing…
        </>
      ) : isReady ? (
        <>
          <Zap className="h-4 w-4" />
          Run AI Analysis
          <Microscope className="h-4 w-4 opacity-60" />
        </>
      ) : (
        <>
          <Microscope className="h-4 w-4 opacity-40" />
          Upload an image to analyze
        </>
      )}
    </motion.button>
  );
}
