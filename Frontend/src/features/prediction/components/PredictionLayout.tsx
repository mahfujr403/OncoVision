import { cn } from '@/lib/utils';
import { PredictionWorkspace } from './PredictionWorkspace';
import { PredictionSidebar } from './PredictionSidebar';
import type { WorkspaceStatus } from '../types';

interface PredictionLayoutProps {
  status?: WorkspaceStatus;
  className?: string;
}

export function PredictionLayout({ status = 'idle', className }: PredictionLayoutProps) {
  return (
    <div
      className={cn(
        'grid gap-6',
        'grid-cols-1 lg:grid-cols-[1fr_320px] xl:grid-cols-[1fr_360px]',
        className,
      )}
    >
      {/* Main workspace — 70% */}
      <PredictionWorkspace status={status} />

      {/* Sticky sidebar — 30% */}
      <div className="lg:sticky lg:top-6 lg:self-start">
        <PredictionSidebar status={status} />
      </div>
    </div>
  );
}
