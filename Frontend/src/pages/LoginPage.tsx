import { useState } from 'react';
import type { Theme } from '@/types';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { Sun, Moon } from 'lucide-react';

interface LoginPageProps {
  onLogin: (email: string, password: string) => void;
  onGoToRegister: () => void;
  theme: Theme;
  onToggleTheme: () => void;
}

function OvLogo() {
  return (
    <div className="flex items-center gap-2.5 justify-center mb-8">
      <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center">
        <svg className="w-5 h-5 text-primary-foreground" viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.75" />
          <circle cx="10" cy="10" r="2.5" fill="currentColor" />
          <line x1="10" y1="1" x2="10" y2="3.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          <line x1="10" y1="16.5" x2="10" y2="19" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          <line x1="1" y1="10" x2="3.5" y2="10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          <line x1="16.5" y1="10" x2="19" y2="10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      </div>
      <div>
        <p className="text-base font-bold text-foreground leading-tight">OncoVision AI</p>
        <p className="text-[11px] text-muted-foreground font-mono leading-tight">Histopathology Analysis Platform</p>
      </div>
    </div>
  );
}

export function LoginPage({ onLogin, onGoToRegister, theme, onToggleTheme }: LoginPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [credentialError, setCredentialError] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});

  function validate() {
    const e: typeof errors = {};
    if (!email.trim()) e.email = 'Email address is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Enter a valid email address.';
    if (!password) e.password = 'Password is required.';
    return e;
  }

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }
    setErrors({});
    setCredentialError(false);
    setLoading(true);
    await new Promise((r) => setTimeout(r, 900));
    setLoading(false);
    if (password.length < 3) {
      setCredentialError(true);
      return;
    }
    onLogin(email, password);
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative">
      {/* Theme toggle */}
      <button
        onClick={onToggleTheme}
        className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      >
        {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>

      <div className="w-full max-w-[360px] fade-up">
        <OvLogo />

        <div className="rounded-xl border border-border bg-card shadow-sm p-7">
          <div className="mb-6">
            <h1 className="text-lg font-semibold text-foreground">Sign in</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Access your OncoVision AI workspace.
            </p>
          </div>

          {credentialError && (
            <div className="mb-5">
              <ErrorState
                title="Invalid credentials"
                message="The email or password you entered is incorrect. Please try again."
                onRetry={() => setCredentialError(false)}
              />
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <Input
              label="Email address"
              type="email"
              placeholder="mahfujr403@oncovision.ai"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setErrors((p) => ({ ...p, email: undefined })); }}
              error={errors.email}
              autoComplete="email"
              autoFocus
            />
            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setErrors((p) => ({ ...p, password: undefined })); }}
              error={errors.password}
              autoComplete="current-password"
            />
            <Button
              type="submit"
              variant="primary"
              size="md"
              className="w-full mt-1"
              loading={loading}
              disabled={loading}
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-5 pt-5 border-t border-border text-center">
            <p className="text-sm text-muted-foreground">
              {"Don't have an account? "}
              <button
                onClick={onGoToRegister}
                className="text-primary hover:underline font-medium"
              >
                Create one
              </button>
            </p>
          </div>
        </div>

        <p className="text-center text-[11px] text-muted-foreground mt-5 leading-relaxed">
          AI-assisted analysis only. Not intended for clinical diagnosis.
          <br />
          <span className="font-mono">Hint: use admin@oncovision.ai to preview admin role</span>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
