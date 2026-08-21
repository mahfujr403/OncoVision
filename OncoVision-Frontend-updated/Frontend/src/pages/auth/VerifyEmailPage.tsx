import { Link } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { ROUTES } from '@/constants/routes';

// There is no email-verification endpoint on the backend today — verified
// against app/api/v1/auth.py, and `UserResponse.is_verified` is set by the
// backend itself with no client-triggerable verification flow to call.
// Rather than simulate a fake "verifying → success" spinner sequence, this
// page states plainly that the feature isn't wired up.
export default function VerifyEmailPage() {
  return (
    <div className="space-y-5 text-center">
      <div className="flex justify-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-amber-500/10">
          <AlertTriangle className="h-7 w-7 text-amber-500" />
        </div>
      </div>
      <div className="space-y-1">
        <h1 className="text-xl font-bold font-display">Email verification unavailable</h1>
        <p className="text-sm text-muted-foreground">
          This isn't wired up to the backend yet — there's no verification endpoint to call.
        </p>
      </div>
      <DemoDataBanner feature="email verification" className="text-left" />
      <div className="space-y-2">
        <Button variant="outline" className="w-full" asChild>
          <Link to={ROUTES.LOGIN}>Go to sign in</Link>
        </Button>
      </div>
    </div>
  );
}
