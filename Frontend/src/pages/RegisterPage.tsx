import { useState } from 'react';
import type { Theme } from '@/types';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Sun, Moon } from 'lucide-react';

interface RegisterPageProps {
  onRegister: (email: string, password: string) => void;
  onGoToLogin: () => void;
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

export function RegisterPage({ onRegister, onGoToLogin, theme, onToggleTheme }: RegisterPageProps) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  function validate() {
    const e: Record<string, string> = {};
    if (!fullName.trim()) e.fullName = 'Full name is required.';
    if (!email.trim()) e.email = 'Email address is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Enter a valid email address.';
    if (!password) e.password = 'Password is required.';
    else if (password.length < 8) e.password = 'Password must be at least 8 characters.';
    if (!confirmPassword) e.confirmPassword = 'Please confirm your password.';
    else if (password !== confirmPassword) e.confirmPassword = 'Passwords do not match.';
    return e;
  }

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }
    setErrors({});
    setLoading(true);
    await new Promise((r) => setTimeout(r, 900));
    setLoading(false);
    onRegister(email, password);
  }

  function clearError(field: string) {
    setErrors((prev) => { const next = { ...prev }; delete next[field]; return next; });
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative">
      <button
        onClick={onToggleTheme}
        className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      >
        {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>

      <div className="w-full max-w-[380px] fade-up">
        <OvLogo />

        <div className="rounded-xl border border-border bg-card shadow-sm p-7">
          <div className="mb-6">
            <h1 className="text-lg font-semibold text-foreground">Create an account</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Join OncoVision AI to begin AI-assisted analysis.
            </p>
          </div>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <Input
              label="Full name"
              type="text"
              placeholder="Dr. Alex Chen"
              value={fullName}
              onChange={(e) => { setFullName(e.target.value); clearError('fullName'); }}
              error={errors.fullName}
              autoComplete="name"
              autoFocus
            />
            <Input
              label="Email address"
              type="email"
              placeholder="you@institution.edu"
              value={email}
              onChange={(e) => { setEmail(e.target.value); clearError('email'); }}
              error={errors.email}
              autoComplete="email"
            />
            <Input
              label="Password"
              type="password"
              placeholder="Minimum 8 characters"
              value={password}
              onChange={(e) => { setPassword(e.target.value); clearError('password'); clearError('confirmPassword'); }}
              error={errors.password}
              hint={!errors.password ? 'At least 8 characters.' : undefined}
              autoComplete="new-password"
            />
            <Input
              label="Confirm password"
              type="password"
              placeholder="Re-enter your password"
              value={confirmPassword}
              onChange={(e) => { setConfirmPassword(e.target.value); clearError('confirmPassword'); }}
              error={errors.confirmPassword}
              autoComplete="new-password"
            />
            <Button
              type="submit"
              variant="primary"
              size="md"
              className="w-full mt-1"
              loading={loading}
              disabled={loading}
            >
              {loading ? 'Creating account…' : 'Create Account'}
            </Button>
          </form>

          <div className="mt-5 pt-5 border-t border-border text-center">
            <p className="text-sm text-muted-foreground">
              Already have an account?{' '}
              <button
                onClick={onGoToLogin}
                className="text-primary hover:underline font-medium"
              >
                Sign in
              </button>
            </p>
          </div>
        </div>

        <p className="text-center text-[11px] text-muted-foreground mt-5 leading-relaxed">
          AI-assisted analysis only. Not intended for clinical diagnosis.
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;
