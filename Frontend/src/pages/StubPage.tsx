import {
  ScanLine,
  History,
  BarChart3,
  User,
  Settings,
  Users,
  ClipboardList,
  Server,
  Activity,
  Construction,
} from 'lucide-react';
import type { PageId } from '@/types';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

const PAGE_META: Record<
  PageId,
  { icon: React.ReactNode; title: string; description: string; phase?: string }
> = {
  dashboard: {
    icon: <BarChart3 className="w-6 h-6" />,
    title: 'Dashboard',
    description: '',
  },
  predict: {
    icon: <ScanLine className="w-6 h-6" />,
    title: 'Prediction Workspace',
    description:
      'Upload a histopathology image to run AI-assisted classification. Supports JPG, PNG, and TIFF formats.',

  },
  history: {
    icon: <History className="w-6 h-6" />,
    title: 'Prediction History',
    description:
      'Browse and search your prediction records with pagination, filtering, and detail views.',
  },
  reports: {
    icon: <BarChart3 className="w-6 h-6" />,
    title: 'Reports',
    description:
      'View prediction reports, download exports, and access detailed analysis summaries.',

  },
  profile: {
    icon: <User className="w-6 h-6" />,
    title: 'Profile',
    description: 'Manage your account information and credentials.',
  },
  settings: {
    icon: <Settings className="w-6 h-6" />,
    title: 'Settings',
    description: 'Configure application preferences and notification settings.',
  },
  'admin-users': {
    icon: <Users className="w-6 h-6" />,
    title: 'User Management',
    description:
      'View and manage registered users, assign roles, and review access levels.',

  },
  'admin-history': {
    icon: <ClipboardList className="w-6 h-6" />,
    title: 'All Prediction History',
    description:
      'Admin view of all prediction records across all users with filtering and export.',

  },
  'admin-system': {
    icon: <Server className="w-6 h-6" />,
    title: 'System',
    description:
      'Inspect model loading status, backend health, and system configuration.',

  },
  'admin-monitoring': {
    icon: <Activity className="w-6 h-6" />,
    title: 'Monitoring',
    description:
      'Real-time system health, API performance, model availability, and prediction activity.',
  },
};

interface StubPageProps {
  pageId: PageId;
  onNavigate: (page: PageId) => void;
}

export function StubPage({ pageId, onNavigate }: StubPageProps) {
  const meta = PAGE_META[pageId] ?? {
    icon: <Construction className="w-6 h-6" />,
    title: pageId,
    description: 'This page is under development.',
  };

  return (
    <div className="p-6 max-w-[1280px] mx-auto">
      <div className="flex flex-col items-center justify-center py-24 px-8 text-center">
        <div className="w-14 h-14 rounded-xl bg-muted flex items-center justify-center text-muted-foreground mb-5">
          {meta.icon}
        </div>
        <div className="flex items-center gap-2 mb-3">
          <h1 className="text-xl font-bold text-foreground">{meta.title}</h1>
          {meta.phase && (
            <Badge variant="outline" className="font-mono">
              {meta.phase}
            </Badge>
          )}
        </div>
        {meta.description && (
          <p className="text-sm text-muted-foreground max-w-md leading-relaxed">
            {meta.description}
          </p>
        )}
        <div className="mt-3 mb-6">
          <Badge variant="warning" dot>
            Implementation pending — backend integration required
          </Badge>
        </div>
        <Button variant="outline" size="sm" onClick={() => onNavigate('dashboard')}>
          ← Back to Dashboard
        </Button>
      </div>
    </div>
  );
}

export default StubPage;
