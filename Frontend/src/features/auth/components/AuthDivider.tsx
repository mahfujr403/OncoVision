import { cn } from '@/lib/utils';

interface AuthDividerProps {
  label?: string;
  className?: string;
}

export function AuthDivider({ label = 'or', className }: AuthDividerProps) {
  return (
    <div className={cn('relative flex items-center gap-3', className)}>
      <div className="flex-1 h-px bg-border" />
      <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">{label}</span>
      <div className="flex-1 h-px bg-border" />
    </div>
  );
}
