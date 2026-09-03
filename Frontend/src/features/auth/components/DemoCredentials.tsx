import { Info } from 'lucide-react';

interface Credential {
  role: string;
  email: string;
  password: string;
}

// Mirrors backend/scripts/seed_demo_users.py — keep these two in sync.
// The backend only has two roles (admin/user); do not add more here
// unless the seed script grows a matching account.
const DEMO_CREDENTIALS: Credential[] = [
  { role: 'Admin', email: 'admin@oncovision.ai', password: 'Demo@Admin123' },
  { role: 'User', email: 'user@oncovision.ai', password: 'Demo@User123' },
];

interface DemoCredentialsProps {
  onSelect?: (email: string, password: string) => void;
}

export function DemoCredentials({ onSelect }: DemoCredentialsProps) {
  return (
    <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 space-y-2">
      <div className="flex items-center gap-1.5 text-xs text-primary font-medium">
        <Info className="h-3.5 w-3.5" />
        Demo accounts
      </div>
      <div className="space-y-1">
        {DEMO_CREDENTIALS.map((c) => (
          <button
            key={c.role}
            type="button"
            onClick={() => onSelect?.(c.email, c.password)}
            className="w-full flex items-center justify-between rounded px-2 py-1.5 text-left text-xs hover:bg-primary/10 transition-colors"
          >
            <span className="font-medium text-foreground">{c.role}</span>
            <span className="font-mono text-muted-foreground truncate ml-2">{c.email}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
