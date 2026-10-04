import { Outlet, Link } from 'react-router-dom';
import { Microscope, ArrowRight, Sun, Moon } from 'lucide-react';
import { APP_NAME } from '@/constants/app';
import { ROUTES } from '@/constants/routes';
import { Button } from '@/components/ui/Button';
import { Footer } from '@/components/layout/Footer';
import { useTheme } from '@/hooks/useTheme';

export function LandingLayout() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen flex flex-col bg-background text-text-primary">
      {/* Top Header Bar */}
      <header className="sticky top-0 z-40 border-b border-border bg-surface/85 backdrop-blur-md transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          {/* Brand Logo */}
          <Link to={ROUTES.LANDING} className="flex items-center gap-2.5 shrink-0 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs transition-transform group-hover:scale-105">
              <Microscope className="h-4.5 w-4.5" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold font-display text-sm tracking-tight text-text-primary">{APP_NAME}</span>
            </div>
          </Link>

          {/* Section Anchor Navigation */}
          <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-text-muted">
            <a href="#features" className="hover:text-text-primary transition-colors">Features</a>
            <a href="#workflow" className="hover:text-text-primary transition-colors">Workflow</a>
            <a href="#technology" className="hover:text-text-primary transition-colors">Technology</a>
          </nav>

          {/* Header Action Buttons */}
          <div className="flex items-center gap-2.5">
            {/* Theme Toggle Button */}
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={toggleTheme}
              className="text-text-muted hover:text-text-primary"
              aria-label="Toggle theme mode"
            >
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>

            {/* Sign In CTA */}
            <Button variant="ghost" size="sm" asChild className="text-xs text-text-secondary hover:text-text-primary">
              <Link to={ROUTES.LOGIN}>Sign in</Link>
            </Button>

            {/* Primary Get Started CTA */}
            <Button size="sm" asChild className="gap-1.5 text-xs font-semibold px-3.5 shadow-xs">
              <Link to={ROUTES.REGISTER}>
                <span>Get started</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Shared Footer */}
      <Footer />
    </div>
  );
}
