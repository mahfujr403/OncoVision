import { FlaskConical } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DemoDataBannerProps {
  /** Short reason shown to the user, e.g. "notifications" or "model benchmarking". */
  feature?: string;
  className?: string;
}

/**
 * Visible, unmissable banner marking a screen (or section of a screen) as
 * demo/placeholder data with no live backend endpoint behind it.
 *
 * Per project rule: unsupported features are never silently faked as real —
 * and they are also never removed outright, just clearly labeled. Place
 * this at the very top of any page/section backed by a `Demo*` type from
 * `@/types`.
 */
export function DemoDataBanner({ feature, className }: DemoDataBannerProps) {
  return (
    <div
      role="status"
      className={cn(
        'flex items-start gap-3 rounded-lg border-2 border-dashed border-amber-500/50 bg-amber-500/10 px-4 py-3',
        className,
      )}
    >
      <FlaskConical className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
      <div className="space-y-0.5">
        <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
          Demo data — not a real API
        </p>
        <p className="text-xs text-amber-700/90 dark:text-amber-400/90">
          {feature ? `The backend has no ${feature} endpoint yet, so ` : 'The backend does not support this yet, so '}
          everything shown here is placeholder content for illustration only. It does not
          reflect real data and no request is sent to the server.
        </p>
      </div>
    </div>
  );
}
