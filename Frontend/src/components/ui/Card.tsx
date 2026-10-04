import { forwardRef, type HTMLAttributes, type ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const cardVariants = cva("rounded-lg border bg-surface text-text-primary", {
  variants: {
    variant: {
      default: "border-border shadow-xs",
      elevated: "border-border-emphasis shadow-md",
      outline: "border-border bg-transparent",
      ghost: "border-transparent bg-surface-raised/40",
      diagnostic: "border-border bg-surface shadow-xs",
    },
    padding: {
      none: "",
      sm: "p-3",
      default: "p-4 md:p-5",
      lg: "p-6",
    },
  },
  defaultVariants: {
    variant: "default",
    padding: "default",
  },
})

interface CardProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, padding }), className)}
      {...props}
    />
  ),
)
Card.displayName = "Card"

export const CardHeader =
  forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
      <div
        ref={ref}
        className={cn("flex flex-col gap-1.5 pb-3", className)}
        {...props}
      />
    ),
  )
CardHeader.displayName = "CardHeader"

interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  as?: "h1" | "h2" | "h3" | "h4"
}

export const CardTitle = forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ className, as: Tag = "h3", ...props }, ref) => (
    <Tag
      ref={ref}
      className={cn(
        "font-semibold text-base leading-tight tracking-tight text-text-primary",
        className,
      )}
      {...props}
    />
  ),
)
CardTitle.displayName = "CardTitle"

export const CardDescription =
  forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
    ({ className, ...props }, ref) => (
      <p
        ref={ref}
        className={cn("text-xs text-text-muted leading-relaxed", className)}
        {...props}
      />
    ),
  )
CardDescription.displayName = "CardDescription"

export const CardContent =
  forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
      <div ref={ref} className={cn("", className)} {...props} />
    ),
  )
CardContent.displayName = "CardContent"

export const CardFooter =
  forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
      <div
        ref={ref}
        className={cn(
          "flex items-center pt-3 border-t border-border-subtle",
          className,
        )}
        {...props}
      />
    ),
  )
CardFooter.displayName = "CardFooter"

// Stat Card
interface StatCardProps {
  label: string
  value: string | number
  delta?: string
  deltaPositive?: boolean
  icon?: ReactNode
  className?: string
}

export function StatCard({
  label,
  value,
  delta,
  deltaPositive,
  icon,
  className,
}: StatCardProps) {
  return (
    <Card className={cn("", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-medium text-text-muted uppercase tracking-wider">
            {label}
          </span>
          <span className="text-2xl font-semibold font-mono tracking-tight text-text-primary tabular-nums">
            {value}
          </span>
          {delta && (
            <span
              className={cn(
                "text-xs font-medium tabular-nums",
                deltaPositive ? "text-success" : "text-error",
              )}
            >
              {deltaPositive ? "↑" : "↓"} {delta}
            </span>
          )}
        </div>
        {icon && (
          <div className="shrink-0 p-2 rounded-md bg-primary-surface text-primary">
            {icon}
          </div>
        )}
      </div>
    </Card>
  )
}

// Metric Card
interface MetricCardProps {
  title: string
  value: string | number
  unit?: string
  description?: string
  className?: string
}

export function MetricCard({
  title,
  value,
  unit,
  description,
  className,
}: MetricCardProps) {
  return (
    <Card variant="ghost" className={cn("", className)}>
      <p className="text-xs font-medium text-text-muted">{title}</p>
      <div className="flex items-baseline gap-1 mt-1">
        <span className="text-xl font-semibold font-mono tabular-nums text-text-primary">
          {value}
        </span>
        {unit && <span className="text-xs text-text-muted">{unit}</span>}
      </div>
      {description && (
        <p className="text-xs text-text-muted mt-0.5">{description}</p>
      )}
    </Card>
  )
}
