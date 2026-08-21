import { cn } from '@/lib/utils';
import { PredictionWorkflowCard } from './PredictionWorkflowCard';
import { PredictionInfoCard } from './PredictionInfoCard';
import type { WorkspaceStatus } from '../types';

interface PredictionSidebarProps {
  status?: WorkspaceStatus;
  className?: string;
}

export function PredictionSidebar({ status = 'idle', className }: PredictionSidebarProps) {
  return (
    <aside
      className={cn('flex flex-col gap-4', className)}
      aria-label="Prediction workspace sidebar"
    >
      <PredictionWorkflowCard status={status} />
      <PredictionInfoCard />
    </aside>
  );
}
