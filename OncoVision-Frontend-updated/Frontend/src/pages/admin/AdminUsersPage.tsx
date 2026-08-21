import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { History } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Avatar } from '@/components/ui/Avatar';
import { SearchBox } from '@/components/ui/SearchBox';
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

// NOTE: the backend has no "invite user" endpoint (accounts are only ever
// created via self-service /auth/register), no per-user profile edit, and
// no "institution" field on User at all. Those were fabricated in the
// previous version of this page and have been removed rather than faked.
// The only real admin actions here are: list users (page/page_size only —
// no server-side search/filter, verified in app/api/v1/admin/users.py),
// activate, and deactivate.
export default function AdminUsersPage() {
  const navigate = useNavigate();
  const { page, pageSize, goToPage } = usePagination();
  const [pageQuery, setPageQuery] = useState('');

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
    const mutation = user.is_active ? deactivate : activate;
    mutation.mutate(user.id, {
      onSuccess: () => toast.success(`${user.full_name} ${user.is_active ? 'deactivated' : 'activated'}.`),
      onError: (err) => toast.error((err as ApiError).message ?? 'Action failed.'),
    });
  };

  return (
    <div className="space-y-5">
      <SectionTitle
        title="User Management"
        description={data ? `${data.pagination.total_records} registered users` : 'Loading…'}
      />

      <div className="flex items-center gap-3">
        <SearchBox
          value={pageQuery}
          onChange={setPageQuery}
          placeholder="Filter this page by name or email…"
          className="max-w-sm"
        />
      </div>

      <Card padding="none">
        {isError ? (
          <ErrorState message="Couldn't load users." onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="divide-y divide-border">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-4 py-3">
                <Skeleton className="h-8 w-8 rounded-full" />
                <Skeleton className="h-3 w-32" />
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-3 w-20" />
              </div>
            ))}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead>Last login</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>
                    <div className="flex items-center gap-2.5">
                      <Avatar src={u.avatar_url ?? undefined} fallback={u.full_name} size="sm" />
                      <div>
                        <p className="text-xs font-medium">{u.full_name}</p>
                        <p className="text-[10px] text-muted-foreground">{u.email}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={u.role === 'admin' ? 'default' : 'secondary'} className="text-[10px]">
                      {ROLE_LABELS[u.role]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={u.is_active ? 'success' : 'destructive'} dot className="text-[10px]">
                      {u.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-[11px] text-muted-foreground">{formatDate(u.created_at)}</TableCell>
                  <TableCell className="text-[11px] text-muted-foreground">
                    {u.last_login ? formatDateTime(u.last_login) : 'Never'}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="xs"
                        className="gap-1"
                        onClick={() => navigate(`${ROUTES.ADMIN_HISTORY}?user_id=${u.id}`)}
                      >
                        <History className="h-3.5 w-3.5" />
                        History
                      </Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => handleToggleActive(u)}
                        loading={activate.isPending || deactivate.isPending}
                      >
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {data && data.pagination.total_pages > 1 && (
        <div className="flex justify-end">
          <Pagination page={page} totalPages={data.pagination.total_pages} onPageChange={goToPage} />
        </div>
      )}
    </div>
  );
}
