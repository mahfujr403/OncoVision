import { Outlet, Link } from 'react-router-dom';
import { Stethoscope } from 'lucide-react';
import { APP_NAME } from '@/constants/app';
import { ROUTES } from '@/constants/routes';
import { Button } from '@/components/ui/Button';
import { Footer } from '@/components/layout/Footer';

export function LandingLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="sticky top-0 z-30 flex h-14 items-center border-b border-border bg-background/80 backdrop-blur-md px-6">
        <Link to={ROUTES.LANDING} className="flex items-center gap-2.5 mr-8">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Stethoscope className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="font-semibold font-display text-sm">{APP_NAME}</span>
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
          <a href="#features" className="hover:text-foreground transition-colors">Features</a>
          <a href="#workflow" className="hover:text-foreground transition-colors">Workflow</a>
          <a href="#technology" className="hover:text-foreground transition-colors">Technology</a>
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="sm" asChild>
            <Link to={ROUTES.LOGIN}>Sign in</Link>
          </Button>
          <Button size="sm" asChild>
            <Link to={ROUTES.REGISTER}>Get started</Link>
          </Button>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <Footer />
    </div>
  );
}
