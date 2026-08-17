import { Link } from 'react-router-dom';
import { ArrowLeft, Clock } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { ROUTES } from '@/constants/routes';

// Password reset is not yet supported by the backend — no /auth/reset-password endpoint exists.
export default function ResetPasswordPage() {
  return (
    <div className="space-y-5 text-center">
      <div className="flex justify-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
          <Clock className="h-7 w-7 text-muted-foreground" />
        </div>
      </div>

      <div className="space-y-2">
        <h1 className="text-2xl font-bold font-display">Coming soon</h1>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Password reset is not yet available. Please contact your system administrator.
        </p>
      </div>

      <Button asChild variant="outline" className="w-full">
        <Link to={ROUTES.LOGIN}>
          <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
          Back to sign in
        </Link>
      </Button>
    </div>
  );
}
