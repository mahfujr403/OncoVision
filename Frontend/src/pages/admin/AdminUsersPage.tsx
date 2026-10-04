import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { History, Users, ShieldCheck, UserCheck, UserX, Clock, Calendar, Mail } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Avatar } from '@/components/ui/Avatar';
import { SearchBox } from '@/components/ui/SearchBox';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { Pagination } from '@/components/ui/Pagination';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { useAdminUsers, useActivateAdminUser, useDeactivateAdminUser } from '@/hooks/queries/useAdminUsers';
import { usePagination } from '@/hooks/usePagination';
import { ROLE_LABELS } from '@/constants/roles';
import { ROUTES } from '@/constants/routes';
import { formatDate, formatDateTime } from '@/utils/formatters';
import type { ApiError, User } from '@/types';

export default function AdminUsersPage() {
  const navigate = useNavigate();
  const { page, pageSize, goToPage } = usePagination();
  const [pageQuery, setPageQuery] = useState('');
  const [activeUserId, setActiveUserId] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useAdminUsers({ page, page_size: pageSize });
  const activate = useActivateAdminUser();
  const deactivate = useDeactivateAdminUser();

  const items = data?.items ?? [];
  const visible = pageQuery
    ? items.filter(
        (u) =>
          u.full_name.toLowerCase().includes(pageQuery.toLowerCase()) ||
          u.email.toLowerCase().includes(pageQuery.toLowerCase()),
      )
    : items;

  const handleToggleActive = (user: User) => {
    setActiveUserId(user.id);
    const mutation = user.is_active ? deactivate : activate;
    mutation.mutate(user.id, {
      onSuccess: () => {
        toast.success(`${user.full_name} has been ${user.is_active ? 'deactivated' : 'activated'}.`);
        setActiveUserId(null);
      },
      onError: (err) => {
        toast.error((err as ApiError).message ?? 'Action failed.');
        setActiveUserId(null);
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Header with operational metadata */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SectionTitle
          title="User Management"
          description="Administrative account oversight, platform role assignment, and access authorization."
        />
        {data && (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs px-2.5 py-1">
              <Users className="h-3.5 w-3.5 mr-1.5 text-primary" />
              <span className="font-semibold text-text-primary tabular-nums">{data.pagination.total_records}</span>
              <span className="ml-1 text-text-muted">Registered Accounts</span>
            </Badge>
          </div>
        )}
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SearchBox
          value={pageQuery}
          onChange={setPageQuery}
          placeholder="Filter accounts by name or email…"
          className="max-w-md w-full"
        />
        {pageQuery && (
          <span className="text-xs text-text-muted font-mono">
            Showing {visible.length} of {items.length} accounts on page
          </span>
        )}
      </div>

      {/* Main Content Area */}
      <Card padding="none">
        {isError ? (
          <ErrorState message="Could not load user accounts from directory service." onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="divide-y divide-border p-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between gap-4 px-4 py-3.5">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-9 w-9 rounded-full" />
                  <div className="space-y-1.5">
                    <Skeleton className="h-3.5 w-36" />
                    <Skeleton className="h-3 w-48" />
                  </div>
                </div>
                <div className="hidden sm:flex items-center gap-6">
                  <Skeleton className="h-5 w-16 rounded-full" />
                  <Skeleton className="h-5 w-16 rounded-full" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-8 w-24 rounded-md" />
              </div>
            ))}
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            icon={<Users className="h-6 w-6 text-text-muted" />}
            title="No user accounts found"
            description={
              pageQuery
                ? `No registered users match "${pageQuery}". Try adjusting your search query.`
                : 'No user accounts are currently registered on this platform.'
            }
          />
        ) : (
          <>
            {/* Desktop Table View */}
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">User Identity</TableHead>
                    <TableHead scope="col">System Role</TableHead>
                    <TableHead scope="col">Account Status</TableHead>
                    <TableHead scope="col">Registered Date</TableHead>
                    <TableHead scope="col">Last Login</TableHead>
                    <TableHead scope="col" className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visible.map((u) => {
                    const isPendingAction = activeUserId === u.id && (activate.isPending || deactivate.isPending);
                    return (
                      <TableRow key={u.id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <Avatar src={u.avatar_url ?? undefined} fallback={u.full_name} size="sm" />
                            <div className="min-w-0">
                              <p className="text-xs font-semibold text-text-primary truncate">{u.full_name}</p>
                              <p className="text-[11px] text-text-muted font-mono truncate">{u.email}</p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={u.role === 'admin' ? 'admin' : 'secondary'}
                            className="text-[10px]"
                          >
                            {u.role === 'admin' && <ShieldCheck className="h-3 w-3 mr-1" />}
                            {ROLE_LABELS[u.role] ?? u.role}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={u.is_active ? 'success' : 'secondary'}
                            dot
                            className="text-[10px]"
                          >
                            {u.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs font-mono tabular-nums text-text-muted">
                          {formatDate(u.created_at)}
                        </TableCell>
                        <TableCell className="text-xs font-mono tabular-nums text-text-muted">
                          {u.last_login ? formatDateTime(u.last_login) : <span className="text-text-muted/60">Never</span>}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="ghost"
                              size="xs"
                              className="gap-1 text-xs"
                              onClick={() => navigate(`${ROUTES.ADMIN_HISTORY}?user_id=${u.id}`)}
                              title={`Inspect prediction history for ${u.full_name}`}
                              aria-label={`View prediction history for ${u.full_name}`}
                            >
                              <History className="h-3.5 w-3.5 text-text-muted" />
                              <span>History</span>
                            </Button>
                            <Button
                              variant={u.is_active ? 'outline' : 'default'}
                              size="xs"
                              className="gap-1 text-xs"
                              onClick={() => handleToggleActive(u)}
                              loading={isPendingAction}
                              disabled={isPendingAction}
                              aria-label={`${u.is_active ? 'Deactivate' : 'Activate'} account for ${u.full_name}`}
                            >
                              {u.is_active ? (
                                <>
                                  <UserX className="h-3.5 w-3.5 text-error" />
                                  <span>Deactivate</span>
                                </>
                              ) : (
                                <>
                                  <UserCheck className="h-3.5 w-3.5" />
                                  <span>Activate</span>
                                </>
                              )}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            {/* Mobile Stacked Card View */}
            <div className="divide-y divide-border md:hidden">
              {visible.map((u) => {
                const isPendingAction = activeUserId === u.id && (activate.isPending || deactivate.isPending);
                return (
                  <div key={u.id} className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2.5">
                        <Avatar src={u.avatar_url ?? undefined} fallback={u.full_name} size="sm" />
                        <div>
                          <p className="text-xs font-semibold text-text-primary">{u.full_name}</p>
                          <div className="flex items-center gap-1 text-[11px] text-text-muted font-mono">
                            <Mail className="h-3 w-3 shrink-0" />
                            <span className="truncate max-w-[180px]">{u.email}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <Badge
                          variant={u.role === 'admin' ? 'admin' : 'secondary'}
                          className="text-[10px]"
                        >
                          {ROLE_LABELS[u.role] ?? u.role}
                        </Badge>
                        <Badge
                          variant={u.is_active ? 'success' : 'secondary'}
                          dot
                          className="text-[10px]"
                        >
                          {u.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-text-muted pt-1 border-t border-border-subtle">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3 text-text-muted shrink-0" />
                        <span>Joined: {formatDate(u.created_at)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-text-muted shrink-0" />
                        <span>Login: {u.last_login ? formatDate(u.last_login) : 'Never'}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-2">
                      <Button
                        variant="ghost"
                        size="xs"
                        className="gap-1 text-xs"
                        onClick={() => navigate(`${ROUTES.ADMIN_HISTORY}?user_id=${u.id}`)}
                      >
                        <History className="h-3.5 w-3.5" />
                        <span>History</span>
                      </Button>
                      <Button
                        variant={u.is_active ? 'outline' : 'default'}
                        size="xs"
                        className="gap-1 text-xs"
                        onClick={() => handleToggleActive(u)}
                        loading={isPendingAction}
                        disabled={isPendingAction}
                      >
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </Card>

      {/* Pagination Footer */}
      {data && data.pagination.total_pages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs font-mono text-text-muted">
            Page {page} of {data.pagination.total_pages} ({data.pagination.total_records} total records)
          </p>
          <Pagination page={page} totalPages={data.pagination.total_pages} onPageChange={goToPage} />
        </div>
      )}
    </div>
  );
}
