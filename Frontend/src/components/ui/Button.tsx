import { forwardRef, type ButtonHTMLAttributes } from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-40 select-none cursor-pointer",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground hover:bg-primary-hover active:scale-[0.99] shadow-xs",
        primary:
          "bg-primary text-primary-foreground hover:bg-primary-hover active:scale-[0.99] shadow-xs",
        destructive:
          "bg-error text-white hover:bg-error/90 active:scale-[0.99] shadow-xs",
        outline:
          "border border-border bg-transparent text-text-primary hover:bg-surface-raised hover:text-text-primary active:scale-[0.99]",
        secondary:
          "bg-surface-raised border border-border text-text-primary hover:bg-surface-raised/80 hover:border-border-emphasis active:scale-[0.99]",
        ghost:
          "text-text-secondary hover:bg-surface-raised hover:text-text-primary active:scale-[0.99]",
        link: "text-primary underline-offset-4 hover:underline p-0 h-auto font-normal",
        accent:
          "bg-accent text-white hover:bg-accent/90 active:scale-[0.99] shadow-xs",
      },
      size: {
        xs: "h-6 px-2.5 text-xs",
        sm: "h-8 px-3 text-xs",
        default: "h-9 px-4 text-sm",
        md: "h-9 px-4 text-sm",
        lg: "h-10 px-6 text-sm font-medium",
        icon: "h-9 w-9 p-0",
        "icon-sm": "h-7 w-7 p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
  icon?: React.ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      loading = false,
      icon,
      children,
      disabled,
      ...props
    },
    ref,
  ) => {
    if (asChild) {
      return (
        <Slot
          ref={ref}
          className={cn(buttonVariants({ variant, size }), className)}
          {...props}
        >
          {children}
        </Slot>
      )
    }

    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <>
            <span
              className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
              aria-hidden="true"
            />
            {children}
          </>
        ) : (
          <>
            {icon}
            {children}
          </>
        )}
      </button>
    )
  },
)

Button.displayName = "Button"

export { buttonVariants }
