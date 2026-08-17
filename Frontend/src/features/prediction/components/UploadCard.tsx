import { AnimatePresence, motion } from 'framer-motion';
import { type FileRejection } from 'react-dropzone';
import { RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { UploadZone } from './UploadZone';
import { ImagePreviewCard } from './ImagePreviewCard';
import { ValidationMessage } from './ValidationMessage';
import type { ImageMeta, UploadState, ValidationError } from '../types';

interface UploadCardProps {
  uploadState: UploadState;
  imageMeta: ImageMeta | null;
  validationError: ValidationError | null;
  onDrop: (files: File[], rejections: FileRejection[]) => void;
  onDragEnter: () => void;
  onDragLeave: () => void;
  onRemove: () => void;
  className?: string;
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
      className={cn('space-y-3', className)}
      aria-label="Image upload section"
    >
      {/* Card header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold tracking-tight">Upload Slide Image</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Histopathology images for lung &amp; colon cancer classification
          </p>
        </div>
        {imageMeta && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRemove}
            className="text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Re-upload
          </Button>
        )}
      </div>

      {/* Zone or preview */}
      <AnimatePresence mode="wait">
        {imageMeta ? (
          <motion.div key="preview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <ImagePreviewCard meta={imageMeta} onRemove={onRemove} />
          </motion.div>
        ) : (
          <motion.div key="zone" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <UploadZone
              uploadState={uploadState}
              onDrop={onDrop}
              onDragEnter={onDragEnter}
              onDragLeave={onDragLeave}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Validation error */}
      <ValidationMessage error={validationError} />

      {/* Validating skeleton */}
      {uploadState === 'validating' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex items-center gap-2.5 text-xs text-muted-foreground"
        >
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Validating image…
        </motion.div>
      )}
    </section>
  );
}
