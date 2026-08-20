import { useState } from 'react';
import type { User, PageId, Theme } from '@/types';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { cn } from '@/lib/utils';

interface AppShellProps {
  user: User;
  activePage: PageId;
  onNavigate: (page: PageId) => void;
  onLogout: () => void;
  theme: Theme;
  onToggleTheme: () => void;
  children: React.ReactNode;
}

export function AppShell({
  user,
  activePage,
  onNavigate,
  onLogout,
  theme,
  onToggleTheme,
  children,
}: AppShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar
        user={user}
        activePage={activePage}
        onNavigate={onNavigate}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((v) => !v)}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
        onLogout={onLogout}
        theme={theme}
        onToggleTheme={onToggleTheme}
      />

      <div
        className={cn(
          'flex flex-col flex-1 overflow-hidden transition-[margin-left] duration-200',
          'ml-0 md:ml-[220px]',
          sidebarCollapsed && 'md:ml-16'
        )}
      >
        <TopBar
          user={user}
          activePage={activePage}
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
          onLogout={onLogout}
          onNavigate={onNavigate}
          theme={theme}
          onToggleTheme={onToggleTheme}
        />

        <main className="flex-1 overflow-y-auto">
          <div className="fade-up">{children}</div>
        </main>
      </div>
    </div>
  );
}

export default AppShell;
