import { AlertCircle, X } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface AuthErrorAlertProps {
  message: string;
  className?: string;
}

export function AuthErrorAlert({ message, className }: AuthErrorAlertProps) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={cn(
        'flex items-start gap-2.5 rounded-lg border border-destructive/30 bg-destructive/8 px-3.5 py-3',
        className,
      )}
    >
      <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" aria-hidden />
      <p className="flex-1 text-sm text-destructive leading-snug">{message}</p>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss error"
        className="shrink-0 text-destructive/60 hover:text-destructive transition-colors"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
