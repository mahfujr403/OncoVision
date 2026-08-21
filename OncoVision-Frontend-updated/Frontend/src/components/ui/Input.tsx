import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  startAdornment?: ReactNode;
  endAdornment?: ReactNode;
  error?: string;
  label?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, startAdornment, endAdornment, error, label, hint, id, ...props }, ref) => {
    const inputId = id ?? (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="flex flex-col gap-1.5 w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="text-xs font-medium text-muted-foreground uppercase tracking-wider"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {startAdornment && (
            <span className="absolute left-3 text-muted-foreground pointer-events-none">
              {startAdornment}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            className={cn(
              'w-full h-9 rounded-md border border-border bg-secondary px-3 py-2 text-sm text-foreground',
              'placeholder:text-muted-foreground/60',
              'focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring',
              'disabled:opacity-40 disabled:cursor-not-allowed',
              'transition-colors duration-150',
              startAdornment && 'pl-9',
              endAdornment && 'pr-9',
              error && 'border-destructive focus:ring-destructive',
              className,
            )}
            {...props}
          />
          {endAdornment && (
            <span className="absolute right-3 text-muted-foreground">
              {endAdornment}
            </span>
          )}
        </div>
        {hint && !error && <p className="text-xs text-muted-foreground">{hint}</p>}
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    );
  },
);

Input.displayName = 'Input';
