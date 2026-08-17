import { Link } from 'react-router-dom';
import { Clock } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { ROUTES } from '@/constants/routes';

// Email verification is not yet supported by the backend — no /auth/verify-email endpoint exists.
export default function VerifyEmailPage() {
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
          Email verification is not yet available. Your account is active immediately after
          registration.
        </p>
      </div>

      <Button asChild className="w-full">
        <Link to={ROUTES.LOGIN}>Sign in</Link>
      </Button>
    </div>
  );
}
