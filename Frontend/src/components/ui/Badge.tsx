import { type HTMLAttributes } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-mono font-medium ring-1 ring-inset transition-colors select-none",
  {
    variants: {
      variant: {
        default: "bg-primary-surface text-primary ring-primary/25",
        primary: "bg-primary-surface text-primary ring-primary/25",
        secondary: "bg-surface-raised text-text-secondary ring-border",
        destructive: "bg-error-surface text-error ring-error/25",
        error: "bg-error-surface text-error ring-error/25",
        success: "bg-success-surface text-success ring-success/25",
        warning: "bg-warning-surface text-warning ring-warning/25",
        info: "bg-info-surface text-info ring-info/25",
        accent: "bg-accent-surface text-accent ring-accent/25",
        outline: "bg-transparent text-text-muted ring-border",
        offline: "bg-surface-raised text-text-muted ring-border",
        admin: "bg-primary-surface text-primary ring-primary/25",
        user: "bg-accent-surface text-accent ring-accent/25",
        // Disease-specific histopathology classes
        lungAca:
          "bg-class-lung-aca/12 text-class-lung-aca ring-class-lung-aca/25",
        lungScc:
          "bg-class-lung-scc/12 text-class-lung-scc ring-class-lung-scc/25",
        colonAca:
          "bg-class-colon-aca/12 text-class-colon-aca ring-class-colon-aca/25",
        lungBenign:
          "bg-class-lung-benign/12 text-class-lung-benign ring-class-lung-benign/25",
        colonBenign:
          "bg-class-colon-benign/12 text-class-colon-benign ring-class-colon-benign/25",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
)

interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean
}

export function Badge({
  className,
  variant,
  dot = false,
  children,
  ...props
}: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full shrink-0",
            variant === "success" && "bg-success",
            (variant === "destructive" || variant === "error") && "bg-error",
            variant === "warning" && "bg-warning",
            variant === "info" && "bg-info",
            (variant === "default" ||
              variant === "primary" ||
              variant === "admin") &&
              "bg-primary",
            (variant === "accent" || variant === "user") && "bg-accent",
            variant === "lungAca" && "bg-class-lung-aca",
            variant === "lungScc" && "bg-class-lung-scc",
            variant === "colonAca" && "bg-class-colon-aca",
            variant === "lungBenign" && "bg-class-lung-benign",
            variant === "colonBenign" && "bg-class-colon-benign",
            (!variant ||
              variant === "secondary" ||
              variant === "outline" ||
              variant === "offline") &&
              "bg-text-muted",
          )}
        />
      )}
      {children}
    </span>
  )
}

export { badgeVariants }
