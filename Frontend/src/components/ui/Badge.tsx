import { type HTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
  {
    variants: {
      variant: {
        default: 'bg-primary/10 text-primary ring-primary/20',
        secondary: 'bg-secondary text-secondary-foreground ring-border',
        destructive: 'bg-destructive/10 text-destructive ring-destructive/20',
        success: 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20',
        warning: 'bg-amber-500/10 text-amber-400 ring-amber-500/20',
        info: 'bg-sky-500/10 text-sky-400 ring-sky-500/20',
        accent: 'bg-accent/10 text-accent ring-accent/20',
        outline: 'bg-transparent text-muted-foreground ring-border',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

export function Badge({ className, variant, dot = false, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            variant === 'success' && 'bg-emerald-400',
            variant === 'destructive' && 'bg-destructive',
            variant === 'warning' && 'bg-amber-400',
            variant === 'info' && 'bg-sky-400',
            variant === 'default' && 'bg-primary',
            (!variant || variant === 'secondary' || variant === 'outline') && 'bg-muted-foreground',
          )}
        />
      )}
      {children}
    </span>
  );
}

export { badgeVariants };
