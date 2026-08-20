import { Bell, CheckCircle2, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { formatRelativeTime } from '@/utils/formatters';
import { cn } from '@/lib/utils';
import type { NotificationLevel } from '@/types';

// DEMO DATA — the backend has no /notifications endpoint.
const NOTIFICATIONS = [
  { id: 'n1', title: 'Prediction completed', message: 'slide_case_048.tiff classified as Lung Adenocarcinoma (97.3% confidence).', level: 'success' as NotificationLevel, isRead: false, createdAt: new Date(Date.now() - 1000 * 60 * 5).toISOString() },
  { id: 'n2', title: 'Model updated', message: 'EfficientNetB4 v2.1 is now active. Accuracy improved by 0.3%.', level: 'info' as NotificationLevel, isRead: false, createdAt: new Date(Date.now() - 1000 * 60 * 60).toISOString() },
  { id: 'n3', title: 'Low confidence warning', message: 'Prediction pred_0041 returned confidence below 75%. Manual review recommended.', level: 'warning' as NotificationLevel, isRead: true, createdAt: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString() },
  { id: 'n4', title: 'System maintenance', message: 'Scheduled maintenance on Jul 15 from 02:00–04:00 UTC. Services may be briefly unavailable.', level: 'info' as NotificationLevel, isRead: true, createdAt: new Date(Date.now() - 86400000).toISOString() },
];

const levelConfig: Record<NotificationLevel, { icon: React.ReactNode; variant: 'success' | 'info' | 'warning' | 'destructive' }> = {
  success: { icon: <CheckCircle2 className="h-4 w-4" />, variant: 'success' },
  info: { icon: <Info className="h-4 w-4" />, variant: 'info' },
  warning: { icon: <AlertTriangle className="h-4 w-4" />, variant: 'warning' },
  error: { icon: <AlertCircle className="h-4 w-4" />, variant: 'destructive' },
};

const unreadCount = NOTIFICATIONS.filter((n) => !n.isRead).length;

export default function NotificationsPage() {
  return (
    <div className="space-y-5 max-w-2xl">
      <SectionTitle
        title="Notifications"
        description={`${unreadCount} unread`}
        action={
          unreadCount > 0 ? (
            <Button variant="ghost" size="sm">Mark all read</Button>
          ) : undefined
        }
      />

      <DemoDataBanner feature="notifications" />

      {NOTIFICATIONS.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Bell className="h-6 w-6" />}
            title="No notifications"
            description="You're all caught up."
          />
        </Card>
      ) : (
        <Card padding="none">
          <div className="divide-y divide-border">
            {NOTIFICATIONS.map((n) => {
              const cfg = levelConfig[n.level];
              return (
                <div
                  key={n.id}
                  className={cn(
                    'flex gap-3 px-4 py-4 transition-colors hover:bg-muted/20',
                    !n.isRead && 'bg-primary/[0.03]',
                  )}
                >
                  <div className={cn('shrink-0 mt-0.5', `text-${cfg.variant === 'destructive' ? 'destructive' : cfg.variant === 'success' ? 'emerald-400' : cfg.variant === 'warning' ? 'amber-400' : 'sky-400'}`)}>
                    {cfg.icon}
                  </div>
                  <div className="flex-1 min-w-0 space-y-0.5">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{n.title}</p>
                      {!n.isRead && <span className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" />}
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">{n.message}</p>
                    <p className="text-[10px] text-muted-foreground/60">{formatRelativeTime(n.createdAt)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
