import { createContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { User, UserRole } from '@/types';
import { setTokens, clearTokens, getAccessToken, getRefreshToken } from '@/api';
import { authService } from '@/features/auth/services/authService';

interface AuthState {
  user: User | null;
  token: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (user: User, accessToken: string, refreshToken: string) => void;
  logout: () => void;
  refreshSession: () => Promise<void>;
  updateUser: (user: Partial<User>) => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    role: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Restore session on mount via GET /auth/me using the persisted access token
  useEffect(() => {
    const storedToken = getAccessToken();
    if (!storedToken) {
      setState((s) => ({ ...s, isLoading: false }));
      return;
    }

    authService
      .getMe()
      .then((user) => {
        setState({
          user,
          token: storedToken,
          role: user.role,
          isAuthenticated: true,
          isLoading: false,
        });
      })
      .catch(() => {
        // Token invalid or expired — clear everything
        clearTokens();
        setState({
          user: null,
          token: null,
          role: null,
          isAuthenticated: false,
          isLoading: false,
        });
      });
  }, []);

  const login = useCallback(
    (user: User, accessToken: string, refreshToken: string) => {
      setTokens(accessToken, refreshToken);
      setState({
        user,
        token: accessToken,
        role: user.role,
        isAuthenticated: true,
        isLoading: false,
      });
    },
    [],
  );

  const logout = useCallback(() => {
    clearTokens();
    setState({
      user: null,
      token: null,
      role: null,
      isAuthenticated: false,
      isLoading: false,
    });
  }, []);

  const refreshSession = useCallback(async () => {
    const storedRefresh = getRefreshToken();
    if (!storedRefresh) {
      logout();
      return;
    }
    try {
      const tokens = await authService.refresh(storedRefresh);
      setTokens(tokens.access_token, tokens.refresh_token);
      setState((s) => ({ ...s, token: tokens.access_token }));
    } catch {
      logout();
    }
  }, [logout]);

  const updateUser = useCallback((partial: Partial<User>) => {
    setState((prev) => {
      if (!prev.user) return prev;
      return { ...prev, user: { ...prev.user, ...partial } };
    });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refreshSession, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}
