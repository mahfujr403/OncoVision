import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ZoomIn, ZoomOut, Maximize2, RotateCcw, ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatFileSize } from '@/utils/formatters';
import { Button } from '@/components/ui/Button';
import type { ImageMeta } from '../types';

interface ImagePreviewCardProps {
  meta: ImageMeta;
  onRemove: () => void;
  className?: string;
}

export function ImagePreviewCard({ meta, onRemove, className }: ImagePreviewCardProps) {
  const [zoom, setZoom] = useState(1);
  const [fullscreen, setFullscreen] = useState(false);

  const zoomIn = () => setZoom((z) => Math.min(z + 0.25, 3));
  const zoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.5));
  const resetZoom = () => setZoom(1);
  const toggleFullscreen = () => setFullscreen((f) => !f);

  return (
    <>
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        transition={{ duration: 0.3 }}
        className={cn('overflow-hidden rounded-xl border border-border bg-card', className)}
      >
        {/* Image area */}
        <div className="relative overflow-hidden bg-black/60" style={{ height: 280 }}>
          <div
            className="h-full w-full overflow-auto"
            style={{ cursor: zoom > 1 ? 'move' : 'default' }}
          >
            <img
              src={meta.previewUrl}
              alt={`Preview of ${meta.file.name}`}
              style={{ transform: `scale(${zoom})`, transformOrigin: 'top left', transition: 'transform 0.2s ease' }}
              className="h-full w-full object-contain"
              draggable={false}
            />
          </div>

          {/* Top-right controls */}
          <div className="absolute right-3 top-3 flex gap-1.5">
            <button
              onClick={zoomOut}
              disabled={zoom <= 0.5}
              aria-label="Zoom out"
              className="flex h-7 w-7 items-center justify-center rounded-md bg-black/50 text-white backdrop-blur-sm hover:bg-black/70 disabled:opacity-30 transition-colors"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={zoomIn}
              disabled={zoom >= 3}
              aria-label="Zoom in"
              className="flex h-7 w-7 items-center justify-center rounded-md bg-black/50 text-white backdrop-blur-sm hover:bg-black/70 disabled:opacity-30 transition-colors"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            {zoom !== 1 && (
              <button
                onClick={resetZoom}
                aria-label="Reset zoom"
                className="flex h-7 w-7 items-center justify-center rounded-md bg-black/50 text-white backdrop-blur-sm hover:bg-black/70 transition-colors"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
            )}
            <button
              onClick={toggleFullscreen}
              aria-label="View fullscreen"
              className="flex h-7 w-7 items-center justify-center rounded-md bg-black/50 text-white backdrop-blur-sm hover:bg-black/70 transition-colors"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Zoom label */}
          {zoom !== 1 && (
            <div className="absolute bottom-3 left-3 rounded-md bg-black/50 px-2 py-0.5 font-mono text-[10px] text-white backdrop-blur-sm">
              {Math.round(zoom * 100)}%
            </div>
          )}
        </div>

        {/* Metadata bar */}
        <div className="flex items-center gap-3 border-t border-border bg-card/60 px-4 py-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10">
            <ImageIcon className="h-4 w-4 text-primary" />
          </div>

          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium leading-tight" title={meta.file.name}>
              {meta.file.name}
            </p>
            <div className="mt-0.5 flex items-center gap-2 text-[10px] text-muted-foreground">
              {meta.width > 0 && (
                <span>{meta.width} × {meta.height} px</span>
              )}
              <span>·</span>
              <span>{formatFileSize(meta.sizeBytes)}</span>
              <span>·</span>
              <span className="font-mono">{meta.ext}</span>
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onRemove}
            aria-label="Remove image"
            className="shrink-0 text-muted-foreground hover:text-destructive"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </motion.div>

      {/* Fullscreen overlay */}
      <AnimatePresence>
        {fullscreen && (
          <motion.div
            key="fullscreen"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/90 backdrop-blur-sm"
            onClick={toggleFullscreen}
          >
            <motion.img
              initial={{ scale: 0.92 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.92 }}
              transition={{ duration: 0.25 }}
              src={meta.previewUrl}
              alt={`Fullscreen preview of ${meta.file.name}`}
              className="max-h-[90vh] max-w-[90vw] object-contain rounded-lg shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            />
            <button
              onClick={toggleFullscreen}
              aria-label="Close fullscreen"
              className="absolute right-6 top-6 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
            <p className="absolute bottom-6 left-1/2 -translate-x-1/2 text-xs text-white/50">
              Click anywhere to close
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
