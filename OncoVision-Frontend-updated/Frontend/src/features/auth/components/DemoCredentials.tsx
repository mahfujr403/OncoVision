import { Info } from 'lucide-react';

interface Credential {
  role: string;
  email: string;
  password: string;
}

const DEMO_CREDENTIALS: Credential[] = [
  { role: 'Admin', email: 'admin@oncovision.ai', password: 'Admin@1234' },
  { role: 'Researcher', email: 'researcher@oncovision.ai', password: 'Researcher@1234' },
  { role: 'Doctor', email: 'doctor@oncovision.ai', password: 'Doctor@1234' },
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
