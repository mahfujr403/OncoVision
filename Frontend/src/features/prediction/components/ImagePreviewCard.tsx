import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  X,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Microscope,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { formatFileSize } from "@/utils/formatters"
import { Button } from "@/components/ui/Button"
import type { ImageMeta } from "../types"

interface ImagePreviewCardProps {
  meta: ImageMeta
  onRemove: () => void
  className?: string
}

export function ImagePreviewCard({
  meta,
  onRemove,
  className,
}: ImagePreviewCardProps) {
  const [zoom, setZoom] = useState(1)
  const [fullscreen, setFullscreen] = useState(false)

  const zoomIn = () => setZoom((z) => Math.min(z + 0.25, 3))
  const zoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.5))
  const resetZoom = () => setZoom(1)
  const toggleFullscreen = () => setFullscreen((f) => !f)

  return (
    <>
      <div
        className={cn(
          "overflow-hidden rounded-xl border border-border bg-surface shadow-xs",
          className,
        )}
      >
        {/* Specimen Viewport */}
        <div
          className="relative overflow-hidden bg-neutral-950"
          style={{ height: 300 }}
        >
          <div
            className="h-full w-full overflow-auto flex items-center justify-center"
            style={{ cursor: zoom > 1 ? "grab" : "default" }}
          >
            <img
              src={meta.previewUrl}
              alt={`Histopathology slide: ${meta.file.name}`}
              style={{
                transform: `scale(${zoom})`,
                transformOrigin: "center center",
                transition: "transform 0.15s ease-out",
              }}
              className="max-h-full max-w-full object-contain"
              draggable={false}
            />
          </div>

          {/* Viewport Control Bar */}
          <div className="absolute right-3 top-3 flex items-center gap-1.5 bg-neutral-900/80 backdrop-blur-xs p-1 rounded-lg border border-white/10 shadow-xs">
            <button
              onClick={zoomOut}
              disabled={zoom <= 0.5}
              aria-label="Zoom out slide"
              className="flex h-7 w-7 items-center justify-center rounded text-neutral-300 hover:text-white hover:bg-white/10 disabled:opacity-30 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={zoomIn}
              disabled={zoom >= 3}
              aria-label="Zoom in slide"
              className="flex h-7 w-7 items-center justify-center rounded text-neutral-300 hover:text-white hover:bg-white/10 disabled:opacity-30 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            {zoom !== 1 && (
              <button
                onClick={resetZoom}
                aria-label="Reset slide zoom"
                className="flex h-7 w-7 items-center justify-center rounded text-neutral-300 hover:text-white hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
            )}
            <div className="h-4 w-px bg-white/15 mx-0.5" />
            <button
              onClick={toggleFullscreen}
              aria-label="View slide in fullscreen"
              className="flex h-7 w-7 items-center justify-center rounded text-neutral-300 hover:text-white hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Zoom Level Indicator */}
          {zoom !== 1 && (
            <div className="absolute bottom-3 left-3 rounded bg-neutral-900/80 px-2 py-0.5 font-mono text-[10px] text-neutral-200 border border-white/10 backdrop-blur-xs">
              {Math.round(zoom * 100)}%
            </div>
          )}
        </div>

        {/* Specimen Metadata Footer */}
        <div className="flex items-center gap-3 border-t border-border bg-surface-raised/40 px-4 py-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Microscope className="h-4 w-4" aria-hidden="true" />
          </div>

          <div className="min-w-0 flex-1">
            <p
              className="truncate text-xs font-semibold text-text-primary"
              title={meta.file.name}
            >
              {meta.file.name}
            </p>
            <div className="mt-0.5 flex items-center gap-2 text-[10px] font-mono text-text-muted">
              {meta.width > 0 && (
                <span>
                  {meta.width} × {meta.height} px
                </span>
              )}
              <span>·</span>
              <span>{formatFileSize(meta.sizeBytes)}</span>
              <span>·</span>
              <span className="uppercase">{meta.ext}</span>
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={onRemove}
            aria-label="Remove and select different slide"
            className="shrink-0 text-text-muted hover:text-error hover:bg-error-surface gap-1"
          >
            <X className="h-3.5 w-3.5" />
            Remove
          </Button>
        </div>
      </div>

      {/* Fullscreen Modal View */}
      <AnimatePresence>
        {fullscreen && (
          <motion.div
            key="fullscreen"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-xs p-4"
            onClick={toggleFullscreen}
          >
            <motion.img
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              transition={{ duration: 0.15 }}
              src={meta.previewUrl}
              alt={`Fullscreen preview of ${meta.file.name}`}
              className="max-h-[90vh] max-w-[90vw] object-contain rounded-lg shadow-2xl border border-white/10"
              onClick={(e) => e.stopPropagation()}
            />
            <button
              onClick={toggleFullscreen}
              aria-label="Close fullscreen view"
              className="absolute right-5 top-5 flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              <X className="h-5 w-5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
