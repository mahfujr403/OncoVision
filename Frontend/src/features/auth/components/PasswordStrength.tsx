import { cn } from '@/lib/utils';

interface PasswordStrengthProps {
  password: string;
  className?: string;
}

interface StrengthResult {
  score: number;
  label: string;
  color: string;
}

function evaluateStrength(password: string): StrengthResult {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const levels: StrengthResult[] = [
    { score: 0, label: 'Too weak', color: 'bg-error' },
    { score: 1, label: 'Weak', color: 'bg-error' },
    { score: 2, label: 'Fair', color: 'bg-warning' },
    { score: 3, label: 'Good', color: 'bg-warning' },
    { score: 4, label: 'Strong', color: 'bg-success' },
    { score: 5, label: 'Very strong', color: 'bg-success' },
  ];

  return { ...levels[Math.min(score, 5)], score };
}

export function PasswordStrength({ password, className }: PasswordStrengthProps) {
  if (!password) return null;
  const { score, label, color } = evaluateStrength(password);

  return (
    <div className={cn('space-y-1.5', className)} aria-label={`Password strength: ${label}`}>
      <div className="flex gap-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className={cn(
              'h-1 flex-1 rounded-full transition-colors duration-300',
              i < score ? color : 'bg-secondary',
            )}
          />
        ))}
      </div>
      <p className={cn('text-[10px] font-medium', score <= 1 ? 'text-error' : score <= 3 ? 'text-warning' : 'text-success')}>
        {label}
      </p>
    </div>
  );
}
