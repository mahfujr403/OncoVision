import React from 'react';
import { Link } from 'react-router-dom';
import { Microscope } from 'lucide-react';
import { cn } from '@/lib/utils';
import { APP_NAME } from '@/constants/app';

export interface BrandIconProps {
  /** Size variant */
  size?: 'sm' | 'md' | 'lg' | 'xl';
  /** Whether to render inside a primary-colored rounded badge or as a bare icon */
  variant?: 'badge' | 'bare';
  /** Additional classes for the container or icon */
  className?: string;
  /** Additional classes for the Lucide icon */
  iconClassName?: string;
  'aria-hidden'?: boolean | 'true' | 'false';
}

const SIZE_CONFIGS = {
  sm: {
    badge: 'h-7 w-7 rounded-md',
    icon: 'h-4 w-4',
    title: 'text-sm font-semibold',
    subtitle: 'text-[10px]',
  },
  md: {
    badge: 'h-8 w-8 rounded-lg',
    icon: 'h-4.5 w-4.5',
    title: 'text-sm font-bold font-display tracking-tight',
    subtitle: 'text-[11px]',
  },
  lg: {
    badge: 'h-9 w-9 rounded-lg',
    icon: 'h-5 w-5',
    title: 'text-base font-bold font-display tracking-tight',
    subtitle: 'text-xs',
  },
  xl: {
    badge: 'h-10 w-10 rounded-xl',
    icon: 'h-5.5 w-5.5',
    title: 'text-lg font-bold font-display tracking-tight',
    subtitle: 'text-xs',
  },
} as const;

/**
 * Standard brand icon for OncoVision AI.
 * Displays the unified Microscope glyph within the brand primary badge.
 */
export const BrandIcon: React.FC<BrandIconProps> = ({
  size = 'md',
  variant = 'badge',
  className,
  iconClassName,
  'aria-hidden': ariaHidden = true,
}) => {
  const config = SIZE_CONFIGS[size];

  if (variant === 'bare') {
    return (
      <Microscope
        className={cn(config.icon, 'text-primary shrink-0', className, iconClassName)}
        aria-hidden={ariaHidden}
      />
    );
  }

  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center bg-primary text-primary-foreground shadow-xs',
        config.badge,
        className
      )}
      aria-hidden={ariaHidden}
    >
      <Microscope className={cn(config.icon, iconClassName)} aria-hidden="true" />
    </div>
  );
};

export interface BrandLogoProps {
  /** Size variant */
  size?: 'sm' | 'md' | 'lg' | 'xl';
  /** Optional link destination (e.g. ROUTES.LANDING or '/') */
  to?: string;
  /** Subtitle text, or `true` for default "Clinical Intelligence" */
  subtitle?: string | boolean;
  /** Collapsed mode: shows only the brand icon */
  collapsed?: boolean;
  /** Icon only mode */
  iconOnly?: boolean;
  /** Custom container class */
  className?: string;
  /** Custom badge class */
  badgeClassName?: string;
  /** Custom title text class */
  textClassName?: string;
  /** Custom subtitle class */
  subtitleClassName?: string;
  /** Optional click handler */
  onClick?: () => void;
}

/**
 * Unified brand logo for OncoVision AI.
 * Used across Landing, Authentication, Navigation Sidebar, Header, and Footer.
 */
export const BrandLogo: React.FC<BrandLogoProps> = ({
  size = 'md',
  to,
  subtitle,
  collapsed = false,
  iconOnly = false,
  className,
  badgeClassName,
  textClassName,
  subtitleClassName,
  onClick,
}) => {
  const config = SIZE_CONFIGS[size];

  const resolvedSubtitle =
    typeof subtitle === 'string'
      ? subtitle
      : subtitle === true
      ? 'Clinical Intelligence'
      : null;

  const content = (
    <div
      className={cn(
        'flex items-center gap-2.5 min-w-0 select-none',
        className
      )}
      onClick={onClick}
    >
      <BrandIcon size={size} className={badgeClassName} />

      {!collapsed && !iconOnly && (
        <div className="flex flex-col min-w-0 overflow-hidden text-left">
          <span
            className={cn(
              'leading-tight text-text-primary truncate',
              config.title,
              textClassName
            )}
          >
            {APP_NAME}
          </span>
          {resolvedSubtitle && (
            <span
              className={cn(
                'text-text-muted mt-0.5 truncate font-sans leading-none',
                config.subtitle,
                subtitleClassName
              )}
            >
              {resolvedSubtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );

  if (to) {
    return (
      <Link
        to={to}
        className="inline-flex items-center shrink-0 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded-lg"
        aria-label={APP_NAME}
      >
        {content}
      </Link>
    );
  }

  return content;
};

export default BrandLogo;
