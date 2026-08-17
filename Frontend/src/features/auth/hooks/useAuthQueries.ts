import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';
import { setTokens, clearTokens, getAccessToken } from '@/api';
import { QUERY_KEYS } from '@/constants/api';
import { ROUTES } from '@/constants/routes';
import type { LoginPayload, RegisterPayload } from '../services/authService';

// ── Current user ──────────────────────────────────────────────────────────────
export function useCurrentUser() {
  const hasToken = Boolean(getAccessToken());
  return useQuery({
    queryKey: QUERY_KEYS.AUTH.ME,
    queryFn: () => authService.getMe(),
    enabled: hasToken,
    retry: false,
    staleTime: 60_000, // 1 min — auth-sensitive, avoid aggressive refetch
    gcTime: 120_000,
  });
}

// ── Login mutation ────────────────────────────────────────────────────────────
export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LoginPayload) => authService.login(payload),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      queryClient.setQueryData(QUERY_KEYS.AUTH.ME, data.user);
    },
  });
}

// ── Register mutation ─────────────────────────────────────────────────────────
export function useRegister() {
  return useMutation({
    mutationFn: (payload: RegisterPayload) => authService.register(payload),
  });
}

// ── Logout mutation ───────────────────────────────────────────────────────────
export function useLogout() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (refreshToken: string) => authService.logout(refreshToken),
    onSettled: () => {
      // Always clear regardless of server response
      clearTokens();
      queryClient.clear();
      navigate(ROUTES.LOGIN, { replace: true });
    },
    onError: () => {
      toast.error('Sign out encountered an issue, but you have been logged out locally.');
    },
  });
}

// ── Logout-all mutation ───────────────────────────────────────────────────────
export function useLogoutAll() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: () => authService.logoutAll(),
    onSuccess: () => {
      toast.success('Signed out from all devices.');
    },
    onSettled: () => {
      clearTokens();
      queryClient.clear();
      navigate(ROUTES.LOGIN, { replace: true });
    },
    onError: () => {
      toast.error('Sign out from all devices encountered an issue.');
    },
  });
}
