import { useRef, useState } from 'react';
import { UploadCloud, ImageIcon, X, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import {
  ACCEPTED_IMAGE_EXTENSIONS,
  ACCEPTED_IMAGE_MIME_TYPES,
  MAX_UPLOAD_SIZE_BYTES,
} from '@/types/prediction';

interface UploadZoneProps {
  file: File | null;
  onFileSelected: (file: File) => void;
  onClear: () => void;
  disabled?: boolean;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/** UX validation only — backend's centralized upload validation (ADR-011) is authoritative. */
function validateFile(file: File): string | null {
  const lowerName = file.name.toLowerCase();
  const hasValidExtension = ACCEPTED_IMAGE_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
  const hasValidMime = file.type === '' || (ACCEPTED_IMAGE_MIME_TYPES as readonly string[]).includes(file.type);

  if (!hasValidExtension || !hasValidMime) {
    return 'Unsupported file type. Allowed types: JPEG, PNG.';
  }
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return 'The uploaded file exceeds the maximum allowed size of 10 MB.';
  }
  return null;
}

export function UploadZone({ file, onFileSelected, onClear, disabled }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    const candidate = fileList[0];
    const error = validateFile(candidate);
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(candidate));
    onFileSelected(candidate);
  }

  function handleClear() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setValidationError(null);
    if (inputRef.current) inputRef.current.value = '';
    onClear();
  }

  if (file && previewUrl) {
    return (
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <div className="flex flex-col sm:flex-row">
          <div className="sm:w-56 shrink-0 bg-muted/40 flex items-center justify-center p-3">
            <img
              src={previewUrl}
              alt={`Preview of ${file.name}`}
              className="max-h-48 w-full object-contain rounded-md"
            />
          </div>
          <div className="flex-1 p-4 flex flex-col justify-between gap-4 min-w-0">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-foreground">
                <ImageIcon className="w-4 h-4 text-muted-foreground shrink-0" />
                <p className="text-sm font-medium truncate">{file.name}</p>
              </div>
              <p className="text-xs text-muted-foreground mt-1 font-mono">
                {formatBytes(file.size)} · {file.type || 'unknown type'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                icon={<RefreshCw className="w-3.5 h-3.5" />}
                onClick={() => inputRef.current?.click()}
                disabled={disabled}
              >
                Replace
              </Button>
              <Button
                variant="ghost"
                size="sm"
                icon={<X className="w-3.5 h-3.5" />}
                onClick={handleClear}
                disabled={disabled}
              >
                Remove
              </Button>
            </div>
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_IMAGE_EXTENSIONS.join(',')}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload histopathology image"
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !disabled) inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (!disabled) handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          'flex flex-col items-center justify-center text-center rounded-lg border-2 border-dashed transition-colors duration-150 py-14 px-6 cursor-pointer',
          isDragging ? 'border-primary bg-primary/5' : 'border-border bg-muted/20 hover:bg-muted/30',
          disabled && 'opacity-50 pointer-events-none cursor-not-allowed'
        )}
      >
        <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center text-primary mb-4">
          <UploadCloud className="w-5 h-5" />
        </div>
        <p className="text-sm font-semibold text-foreground">
          Drag and drop an image, or click to browse
        </p>
        <p className="text-xs text-muted-foreground mt-1.5 font-mono">
          Supported: JPEG, PNG · Max 10 MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_IMAGE_EXTENSIONS.join(',')}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      {validationError && (
        <ErrorState title="Upload failed" message={validationError} variant="banner" />
      )}
    </div>
  );
}

export default UploadZone;
