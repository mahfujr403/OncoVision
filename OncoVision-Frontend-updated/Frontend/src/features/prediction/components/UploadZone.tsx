import { useCallback } from 'react';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { motion } from 'framer-motion';
import { Upload, ImagePlus, ClipboardPaste } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ACCEPTED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES } from '@/constants/app';
import type { UploadState } from '../types';

interface UploadZoneProps {
  uploadState: UploadState;
  onDrop: (files: File[], rejections: FileRejection[]) => void;
  onDragEnter: () => void;
  onDragLeave: () => void;
  className?: string;
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
  });

  // Expose input for keyboard trigger
  const { ref: dzRef, ...rootProps } = getRootProps();
  const setRef = useCallback(
    (el: HTMLDivElement | null) => {
      if (typeof dzRef === 'function') dzRef(el);
      else if (dzRef && 'current' in dzRef) (dzRef as React.MutableRefObject<HTMLDivElement | null>).current = el;
    },
    [dzRef],
  );

  const isDragging = isDragActive || uploadState === 'dragging';

  return (
    <div
      ref={setRef}
      {...rootProps}
      role="button"
      tabIndex={0}
      aria-label="Upload histopathology image. Click, drag and drop, or press Enter to browse files."
      className={cn(
        'group relative flex flex-col items-center justify-center gap-5 rounded-xl border-2 border-dashed p-10 text-center transition-all duration-300 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        isDragging
          ? 'border-primary bg-primary/5 shadow-lg shadow-primary/10'
          : uploadState === 'error'
            ? 'border-destructive/40 bg-destructive/3 hover:border-destructive/60'
            : 'border-border/60 bg-card/40 hover:border-primary/40 hover:bg-card/70',
        className,
      )}
    >
      <input {...getInputProps()} aria-hidden="true" />

      {/* Animated background blob on drag */}
      {isDragging && (
        <motion.div
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1.5, opacity: 0.06 }}
          className="pointer-events-none absolute inset-0 rounded-xl bg-primary"
        />
      )}

      {/* Icon cluster */}
      <motion.div
        animate={isDragging ? { scale: 1.12, y: -4 } : { scale: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 24 }}
        className="relative flex h-16 w-16 items-center justify-center"
      >
        {/* Outer ring */}
        <motion.div
          animate={isDragging ? { scale: 1.2, opacity: 1 } : { scale: 1, opacity: 0 }}
          className="absolute inset-0 rounded-full border-2 border-dashed border-primary/40"
        />
        <div
          className={cn(
            'flex h-14 w-14 items-center justify-center rounded-full transition-colors duration-300',
            isDragging
              ? 'bg-primary/20'
              : uploadState === 'error'
                ? 'bg-destructive/10'
                : 'bg-secondary group-hover:bg-primary/10',
          )}
        >
          {isDragging ? (
            <ImagePlus className="h-7 w-7 text-primary" />
          ) : (
            <Upload
              className={cn(
                'h-7 w-7 transition-colors duration-300',
                uploadState === 'error' ? 'text-destructive' : 'text-muted-foreground group-hover:text-primary',
              )}
            />
          )}
        </div>
      </motion.div>

      {/* Copy */}
      <div className="space-y-1.5">
        <p className="text-sm font-semibold tracking-tight">
          {isDragging ? 'Release to upload' : 'Drop your slide image here'}
        </p>
        <p className="text-xs text-muted-foreground">
          or{' '}
          <span className="text-primary underline-offset-2 hover:underline cursor-pointer">
            click to browse files
          </span>
        </p>
      </div>

      {/* Format tags */}
      <div className="flex flex-wrap justify-center gap-1.5">
        {['JPG', 'JPEG', 'PNG', 'TIFF'].map((fmt) => (
          <span
            key={fmt}
            className="rounded-full border border-border/60 bg-secondary/60 px-2.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground"
          >
            {fmt}
          </span>
        ))}
        <span className="rounded-full border border-border/60 bg-secondary/60 px-2.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground">
          ≤ 50 MB
        </span>
      </div>

      {/* Paste hint */}
      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground/50">
        <ClipboardPaste className="h-3 w-3" aria-hidden />
        <span>
          You can also paste an image with{' '}
          <kbd className="rounded border border-border/50 px-1 py-0.5 font-mono text-[9px]">Ctrl+V</kbd>
        </span>
      </div>
    </div>
  );
}
