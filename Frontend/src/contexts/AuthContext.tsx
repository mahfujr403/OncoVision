import { createContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { User, AuthTokens, UserRole } from '@/types';
import { getAccessToken, clearTokens } from '@/api';
import { authService } from '@/features/auth/services/authService';

interface AuthState {
  user: User | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  /** Called by LoginPage after authService.login() has already stored tokens. */
  login: (tokens: AuthTokens, user: User) => void;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  updateUser: (user: Partial<User>) => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    role: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Real session restoration: an access token surviving in localStorage is
  // not proof of a valid session by itself, so we confirm it against the
  // backend via GET /auth/me. The axios interceptor will transparently use
  // the refresh token if the access token has expired.
  useEffect(() => {
    let cancelled = false;

    async function restore() {
      const token = getAccessToken();
      if (!token) {
        setState((s) => ({ ...s, isLoading: false }));
        return;
      }
      try {
        const user = await authService.getMe();
        if (!cancelled) {
          setState({ user, role: user.role, isAuthenticated: true, isLoading: false });
        }
      } catch {
        if (!cancelled) {
          clearTokens();
          setState({ user: null, role: null, isAuthenticated: false, isLoading: false });
        }
      }
    }

    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback((_tokens: AuthTokens, user: User) => {
    // Tokens are already persisted by authService.login(); this just syncs
    // React state so the UI reacts immediately.
    setState({ user, role: user.role, isAuthenticated: true, isLoading: false });
  }, []);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      setState({ user: null, role: null, isAuthenticated: false, isLoading: false });
    }
  }, []);

  const logoutAll = useCallback(async () => {
    try {
      await authService.logoutAll();
    } finally {
      setState({ user: null, role: null, isAuthenticated: false, isLoading: false });
    }
  }, []);

  // NOTE: there is no PATCH /auth/me (or any profile-update endpoint) on the
  // backend today. This only updates local React state for optimistic UI —
  // it does NOT persist anything. ProfilePage must show a "not saved to
  // server" notice wherever it calls this. See DemoDataBanner usage there.
  const updateUser = useCallback((partial: Partial<User>) => {
    setState((prev) => (prev.user ? { ...prev, user: { ...prev.user, ...partial } } : prev));
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, logoutAll, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}
