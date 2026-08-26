import { Outlet, Link } from 'react-router-dom';
import { Stethoscope } from 'lucide-react';
import { APP_NAME } from '@/constants/app';
import { Footer } from '@/components/layout/Footer';

export function AuthLayout() {
  return (
    <div className="min-h-screen grid md:grid-cols-2 bg-background">
      {/* Left panel — branding */}
      <div className="hidden md:flex flex-col justify-between p-10 bg-card border-r border-border relative overflow-hidden">
        {/* Grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />

        <Link to="/" className="flex items-center gap-2.5 relative z-10">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
            <Stethoscope className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-semibold font-display text-base">{APP_NAME}</span>
        </Link>

        <div className="relative z-10 space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
            <span className="text-xs text-primary font-medium">AI-Powered Pathology</span>
          </div>
          <h1 className="text-3xl font-bold font-display leading-tight">
            Precision Cancer<br />
            <span className="text-primary">Classification</span>
          </h1>
          <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">
            A three-model deep learning ensemble analyzes lung and colon cancer histopathology images, with per-model confidence and agreement scoring on every prediction.
          </p>

          <div className="grid grid-cols-3 gap-3 pt-2">
            {[
              { label: 'Models', value: 'Three' },
              { label: 'Technology', value: 'Ensemble' },
              { label: 'Classes', value: 'Five' },
            ].map((stat) => (
              <div key={stat.label} className="rounded-lg border border-border bg-secondary/30 p-3">
                <p className="text-xl font-bold font-mono text-primary">{stat.value}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>

        <p className="text-[10px] text-muted-foreground relative z-10">
          © 2026 {APP_NAME}. For research and educational use only — not clinically approved.
        </p>
      </div>

      {/* Right panel — form */}
      <div className="flex items-center justify-center p-6 md:p-10">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <Link to="/" className="flex items-center gap-2 mb-8 md:hidden">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Stethoscope className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-semibold font-display">{APP_NAME}</span>
          </Link>

          <Outlet />
        </div>
      </div>
    </div>
  
  );
}
