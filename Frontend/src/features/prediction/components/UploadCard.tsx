import { AnimatePresence, motion } from "framer-motion"
import { type FileRejection } from "react-dropzone"
import { RefreshCw, Microscope } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/Button"
import { UploadZone } from "./UploadZone"
import { ImagePreviewCard } from "./ImagePreviewCard"
import { ValidationMessage } from "./ValidationMessage"
import type { ImageMeta, UploadState, ValidationError } from "../types"

interface UploadCardProps {
  uploadState: UploadState
  imageMeta: ImageMeta | null
  validationError: ValidationError | null
  onDrop: (files: File[], rejections: FileRejection[]) => void
  onDragEnter: () => void
  onDragLeave: () => void
  onRemove: () => void
  className?: string
}

export function UploadCard({
  uploadState,
  imageMeta,
  validationError,
  onDrop,
  onDragEnter,
  onDragLeave,
  onRemove,
  className,
}: UploadCardProps) {
  return (
    <section
      className={cn("space-y-3.5", className)}
      aria-label="Histopathology specimen upload section"
    >
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
            <Microscope className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-text-primary">
              Histopathology Specimen
            </h2>
            <p className="text-xs text-text-muted">
              Select or drop an H&amp;E stained biopsy slide image
            </p>
          </div>
        </div>

        {imageMeta && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRemove}
            className="text-text-secondary hover:text-text-primary gap-1.5"
            aria-label="Re-upload or replace image"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Replace Slide
          </Button>
        )}
      </div>

      {/* Upload Zone or Preview */}
      <AnimatePresence mode="wait">
        {imageMeta ? (
          <motion.div
            key="preview"
            initial={{ opacity: 0, scale: 0.99 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.99 }}
            transition={{ duration: 0.2 }}
          >
            <ImagePreviewCard meta={imageMeta} onRemove={onRemove} />
          </motion.div>
        ) : (
          <motion.div
            key="zone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <UploadZone
              uploadState={uploadState}
              onDrop={onDrop}
              onDragEnter={onDragEnter}
              onDragLeave={onDragLeave}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Validation error message */}
      <ValidationMessage error={validationError} />

      {/* Validation progress indicator */}
      {uploadState === "validating" && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex items-center gap-2.5 text-xs text-text-muted"
          role="status"
        >
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Verifying slide format and dimensions…
        </motion.div>
      )}
    </section>
  )
}
