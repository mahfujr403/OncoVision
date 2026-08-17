import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const cardVariants = cva('rounded-lg border bg-card text-card-foreground', {
  variants: {
    variant: {
      default: 'border-border',
      elevated: 'border-border shadow-lg shadow-black/20',
      outline: 'border-border bg-transparent',
      ghost: 'border-transparent bg-muted/40',
    },
    padding: {
      none: '',
      sm: 'p-3',
      default: 'p-4',
      lg: 'p-6',
    },
  },
  defaultVariants: {
    variant: 'default',
    padding: 'default',
  },
});

interface CardProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof cardVariants> {}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, ...props }, ref) => (
    <div ref={ref} className={cn(cardVariants({ variant, padding }), className)} {...props} />
  ),
);
Card.displayName = 'Card';

export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col gap-1 pb-3', className)} {...props} />
  ),
);
CardHeader.displayName = 'CardHeader';

interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  as?: 'h1' | 'h2' | 'h3' | 'h4';
}

export const CardTitle = forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ className, as: Tag = 'h3', ...props }, ref) => (
    <Tag ref={ref} className={cn('font-semibold text-base leading-tight', className)} {...props} />
  ),
);
CardTitle.displayName = 'CardTitle';

export const CardDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-xs text-muted-foreground', className)} {...props} />
  ),
);
CardDescription.displayName = 'CardDescription';

export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('', className)} {...props} />
  ),
);
CardContent.displayName = 'CardContent';

export const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center pt-3 border-t border-border', className)} {...props} />
  ),
);
CardFooter.displayName = 'CardFooter';

// Stat Card
interface StatCardProps {
  label: string;
  value: string | number;
  delta?: string;
  deltaPositive?: boolean;
  icon?: ReactNode;
  className?: string;
}

export function StatCard({ label, value, delta, deltaPositive, icon, className }: StatCardProps) {
  return (
    <Card className={cn('', className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{label}</span>
          <span className="text-2xl font-semibold font-mono tracking-tight">{value}</span>
          {delta && (
            <span className={cn('text-xs font-medium', deltaPositive ? 'text-emerald-400' : 'text-destructive')}>
              {deltaPositive ? '↑' : '↓'} {delta}
            </span>
          )}
        </div>
        {icon && (
          <div className="shrink-0 p-2 rounded-md bg-primary/10 text-primary">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

// Metric Card
interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  description?: string;
  className?: string;
}

export function MetricCard({ title, value, unit, description, className }: MetricCardProps) {
  return (
    <Card variant="ghost" className={cn('', className)}>
      <p className="text-xs text-muted-foreground">{title}</p>
      <div className="flex items-baseline gap-1 mt-1">
        <span className="text-xl font-semibold font-mono">{value}</span>
        {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
      </div>
      {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
    </Card>
  );
}
