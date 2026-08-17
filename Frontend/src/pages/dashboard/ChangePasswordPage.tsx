import { Link } from 'react-router-dom';
import { Clock, ArrowLeft } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { ROUTES } from '@/constants/routes';

// Change password via the API is not yet implemented by the backend.
// Showing a clear "coming soon" state instead of a non-functional form.
export default function ChangePasswordPage() {
  return (
    <div className="space-y-5 max-w-lg">
      <SectionTitle
        title="Change Password"
        description="Update your account password"
      />

      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
            <Clock className="h-7 w-7 text-muted-foreground" />
          </div>
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Coming soon</p>
            <p className="text-xs text-muted-foreground leading-relaxed max-w-xs">
              Password management via the API is not yet available. Contact your system
              administrator to update your password.
            </p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to={ROUTES.PROFILE}>
              <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
              Back to profile
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
