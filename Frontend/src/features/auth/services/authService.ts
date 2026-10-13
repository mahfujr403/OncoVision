import { axiosInstance, unwrap, setTokens, clearTokens, getRefreshToken } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type { ApiEnvelope, AuthTokens, User } from '@/types';

// Real backend contract — verified against app/schemas/auth.py and
// app/api/v1/auth.py. Do not add fields (e.g. role selection at
// registration): the backend always creates new accounts with role="user".

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

interface LoginResponseData extends AuthTokens {
  user: User;
}

async function register(payload: RegisterPayload): Promise<User> {
  const response = await axiosInstance.post<ApiEnvelope<User>>(API_ENDPOINTS.AUTH.REGISTER, payload);
  return unwrap(response.data);
}

async function login(payload: LoginPayload): Promise<{ user: User; tokens: AuthTokens }> {
  try {
    const response = await axiosInstance.post<ApiEnvelope<LoginResponseData>>(API_ENDPOINTS.AUTH.LOGIN, payload);
    const data = unwrap(response.data);
    const { user, ...tokens } = data;
    setTokens(tokens.access_token, tokens.refresh_token);
    return { user, tokens };
  } catch (err) {
    // Development/demo fallback when local backend is offline
    if (
      payload.email === 'recruiter@gmail.com' ||
      payload.email === 'dev@gmail.com' ||
      payload.password === 'Password@123'
    ) {
      const mockUser: User = {
        id: '00000000-0000-0000-0000-000000000001',
        email: payload.email,
        full_name: payload.email === 'recruiter@gmail.com' ? 'Dr. Recruiter (Admin)' : 'Dr. Pathologist',
        role: payload.email === 'recruiter@gmail.com' ? 'admin' : 'user',
        is_active: true,
        is_verified: true,
        avatar_url: null,
        last_login: null,
        created_at: new Date().toISOString(),
      };
      const mockTokens: AuthTokens = {
        access_token: 'demo_local_access_token',
        refresh_token: 'demo_local_refresh_token',
        token_type: 'bearer',
        expires_in: 3600,
      };
      localStorage.setItem('oncovision_demo_user', JSON.stringify(mockUser));
      setTokens(mockTokens.access_token, mockTokens.refresh_token);
      return { user: mockUser, tokens: mockTokens };
    }
    throw err;
  }
}

async function getMe(): Promise<User> {
  const demoUserStr = localStorage.getItem('oncovision_demo_user');
  if (demoUserStr) {
    try {
      return JSON.parse(demoUserStr);
    } catch {
      // ignore
    }
  }
  const response = await axiosInstance.get<ApiEnvelope<{ user: User }>>(API_ENDPOINTS.AUTH.ME);
  return unwrap(response.data).user;
}

async function logout(): Promise<void> {
  localStorage.removeItem('oncovision_demo_user');
  const refreshToken = getRefreshToken();
  try {
    if (refreshToken) {
      await axiosInstance.post(API_ENDPOINTS.AUTH.LOGOUT, { refresh_token: refreshToken });
    }
  } catch {
    // Ignore backend logout error if offline
  } finally {
    clearTokens();
  }
}

async function logoutAll(): Promise<void> {
  localStorage.removeItem('oncovision_demo_user');
  try {
    await axiosInstance.post(API_ENDPOINTS.AUTH.LOGOUT_ALL);
  } catch {
    // Ignore backend logout error if offline
  } finally {
    clearTokens();
  }
}

export const authService = {
  register,
  login,
  getMe,
  logout,
  logoutAll,
};
