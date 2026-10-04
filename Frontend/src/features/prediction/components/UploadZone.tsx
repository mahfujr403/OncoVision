import { useCallback } from "react"
import { useDropzone, type FileRejection } from "react-dropzone"
import { motion } from "framer-motion"
import { Microscope, ImagePlus, ClipboardPaste } from "lucide-react"
import { cn } from "@/lib/utils"
import { ACCEPTED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES } from "@/constants/app"
import type { UploadState } from "../types"

interface UploadZoneProps {
  uploadState: UploadState
  onDrop: (files: File[], rejections: FileRejection[]) => void
  onDragEnter: () => void
  onDragLeave: () => void
  className?: string
}

export function UploadZone({
  uploadState,
  onDrop,
  onDragEnter,
  onDragLeave,
  className,
}: UploadZoneProps) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDragEnter,
    onDragLeave,
    accept: ACCEPTED_IMAGE_TYPES,
    maxSize: MAX_IMAGE_SIZE_BYTES,
    maxFiles: 1,
    noClick: false,
    noKeyboard: false,
  })

  const { ref: dzRef, ...rootProps } = getRootProps()
  const setRef = useCallback(
    (el: HTMLDivElement | null) => {
      if (typeof dzRef === "function") dzRef(el)
      else if (dzRef && "current" in dzRef)
        (dzRef as React.MutableRefObject<HTMLDivElement | null>).current = el
    },
    [dzRef],
  )

  const isDragging = isDragActive || uploadState === "dragging"

  return (
    <div
      ref={setRef}
      {...rootProps}
      role="button"
      tabIndex={0}
      aria-label="Upload histopathology slide image. Click, drag and drop, or press Enter to browse files."
      className={cn(
        "group relative flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed p-8 md:p-10 text-center transition-all duration-200 cursor-pointer",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        isDragging
          ? "border-primary bg-primary/10 shadow-xs"
          : uploadState === "error"
            ? "border-error/40 bg-error-surface/40 hover:border-error/60"
            : "border-border bg-surface hover:border-primary/50 hover:bg-surface-raised/40",
        className,
      )}
    >
      <input {...getInputProps()} aria-hidden="true" />

      {/* Laboratory Specimen Icon Area */}
      <motion.div
        animate={isDragging ? { scale: 1.08, y: -2 } : { scale: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 24 }}
        className="relative flex h-14 w-14 items-center justify-center"
      >
        <div
          className={cn(
            "flex h-14 w-14 items-center justify-center rounded-xl border transition-colors duration-200",
            isDragging
              ? "bg-primary/20 border-primary text-primary"
              : uploadState === "error"
                ? "bg-error-surface border-error text-error"
                : "bg-surface-raised border-border-subtle text-text-secondary group-hover:border-primary/40 group-hover:text-primary",
          )}
        >
          {isDragging ? (
            <ImagePlus className="h-6 w-6 text-primary" />
          ) : (
            <Microscope className="h-6 w-6" />
          )}
        </div>
      </motion.div>

      {/* Copy */}
      <div className="space-y-1">
        <p className="text-sm font-semibold tracking-tight text-text-primary">
          {isDragging
            ? "Release to stage slide specimen"
            : "Select or drag histopathology slide"}
        </p>
        <p className="text-xs text-text-muted">
          Supported high-resolution formats for lung &amp; colon biopsy tissue
        </p>
      </div>

      {/* Format tags */}
      <div className="flex flex-wrap justify-center gap-1.5 pt-1">
        {["JPEG", "PNG", "TIFF"].map((fmt) => (
          <span
            key={fmt}
            className="rounded-md border border-border-subtle bg-surface-raised px-2 py-0.5 font-mono text-[10px] font-medium text-text-muted"
          >
            {fmt}
          </span>
        ))}
        <span className="rounded-md border border-border-subtle bg-surface-raised px-2 py-0.5 font-mono text-[10px] font-medium text-text-muted">
          ≤ 10 MB
        </span>
      </div>

      {/* Paste hint */}
      <div className="flex items-center gap-1.5 text-[11px] text-text-muted pt-1">
        <ClipboardPaste
          className="h-3.5 w-3.5 text-text-muted/70"
          aria-hidden="true"
        />
        <span>
          Clipboard paste supported with{" "}
          <kbd className="rounded border border-border-subtle bg-surface-raised px-1 py-0.5 font-mono text-[10px] text-text-secondary">
            Ctrl+V
          </kbd>
        </span>
      </div>
    </div>
  )
}
