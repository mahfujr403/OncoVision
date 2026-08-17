// Phase 6 — Admin user management (GET /admin/users, activate/deactivate) not yet implemented.
// This is a placeholder page that will be replaced with real API integration in Phase 6.
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardContent } from '@/components/ui/Card';
import { Clock } from 'lucide-react';

export default function AdminUsersPage() {
  return (
    <div className="space-y-5">
      <SectionTitle
        title="User Management"
        description="Manage registered users — activate and deactivate accounts"
      />
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
            <Clock className="h-7 w-7 text-muted-foreground" />
          </div>
          <p className="text-sm font-medium">Coming in Phase 6</p>
          <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
            Real user management via{' '}
            <code className="font-mono text-[11px]">GET /admin/users</code> will be
            integrated in Phase 6.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
