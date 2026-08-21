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
  const response = await axiosInstance.post<ApiEnvelope<LoginResponseData>>(API_ENDPOINTS.AUTH.LOGIN, payload);
  const data = unwrap(response.data);
  const { user, ...tokens } = data;
  setTokens(tokens.access_token, tokens.refresh_token);
  return { user, tokens };
}

async function getMe(): Promise<User> {
  // NOTE: unlike POST /auth/login (which returns a flat { user, access_token, ... }
  // envelope, matching LoginResponseData), GET /auth/me nests the user one level
  // deeper as { user: {...} } with no sibling fields — verified against
  // app/api/v1/auth.py's get_me() handler. Do not flatten this contract away by
  // changing the backend; the two endpoints are intentionally shaped differently.
  const response = await axiosInstance.get<ApiEnvelope<{ user: User }>>(API_ENDPOINTS.AUTH.ME);
  return unwrap(response.data).user;
}

async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();
  try {
    if (refreshToken) {
      await axiosInstance.post(API_ENDPOINTS.AUTH.LOGOUT, { refresh_token: refreshToken });
    }
  } finally {
    clearTokens();
  }
}

async function logoutAll(): Promise<void> {
  try {
    await axiosInstance.post(API_ENDPOINTS.AUTH.LOGOUT_ALL);
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
