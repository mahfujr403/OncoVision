import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { ROUTES } from '@/constants/routes';

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-6">
      <div className="text-center space-y-5">
        <div className="text-8xl font-bold font-mono text-primary/20 select-none">404</div>
        <div className="space-y-2">
          <h1 className="text-2xl font-bold font-display">Page not found</h1>
          <p className="text-sm text-muted-foreground max-w-xs mx-auto">
            The page you're looking for doesn't exist or has been moved.
          </p>
        </div>
        <div className="flex justify-center gap-3">
          <Button variant="outline" onClick={() => window.history.back()}>
            <ArrowLeft className="h-4 w-4" />
            Go back
          </Button>
          <Button asChild>
            <Link to={ROUTES.DASHBOARD}>Dashboard</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
