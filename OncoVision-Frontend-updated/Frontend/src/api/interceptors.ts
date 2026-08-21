import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import axios from 'axios';
import type { ApiEnvelope, ApiError } from '@/types';
import { API_BASE_URL, API_ENDPOINTS } from '@/constants/api';

const ACCESS_TOKEN_KEY = 'oncovision_access_token';
const REFRESH_TOKEN_KEY = 'oncovision_refresh_token';

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// A bare axios client (no interceptors) used only for the refresh call
// itself, so refreshing never recurses through the 401 handler below.
const refreshClient = axios.create({ baseURL: API_BASE_URL, timeout: 15_000 });

// --- Single-flight refresh + pending-request queue --------------------------
// Prevents concurrent 401s from firing multiple /auth/refresh calls and
// queues requests that arrive while a refresh is already in progress, per
// project rule: "no duplicate refresh requests, queue requests during
// refresh, avoid infinite refresh loops."
let isRefreshing = false;
let refreshWaiters: Array<(token: string | null) => void> = [];

function onRefreshed(token: string | null): void {
  refreshWaiters.forEach((resolve) => resolve(token));
  refreshWaiters = [];
}

function waitForRefresh(): Promise<string | null> {
  return new Promise((resolve) => {
    refreshWaiters.push(resolve);
  });
}

async function performRefresh(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const response = await refreshClient.post<ApiEnvelope<{ access_token: string; refresh_token: string }>>(
      API_ENDPOINTS.AUTH.REFRESH,
      { refresh_token: refreshToken },
    );
    const data = response.data.data;
    if (!data) return null;
    setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    return null;
  }
}

function redirectToLogin(): void {
  clearTokens();
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

export function setupInterceptors(instance: AxiosInstance): void {
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error: AxiosError) => Promise.reject(error),
  );

  instance.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error: AxiosError<ApiEnvelope<unknown>>) => {
      const originalRequest = error.config as
        | (InternalAxiosRequestConfig & { _retry?: boolean })
        | undefined;

      const isAuthEndpoint =
        originalRequest?.url?.includes(API_ENDPOINTS.AUTH.LOGIN) ||
        originalRequest?.url?.includes(API_ENDPOINTS.AUTH.REFRESH) ||
        originalRequest?.url?.includes(API_ENDPOINTS.AUTH.REGISTER);

      if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !isAuthEndpoint) {
        originalRequest._retry = true;

        if (isRefreshing) {
          // A refresh is already in flight — wait for it instead of firing another.
          const token = await waitForRefresh();
          if (!token) return Promise.reject(buildApiError(error));
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return instance(originalRequest);
        }

        isRefreshing = true;
        const newToken = await performRefresh();
        isRefreshing = false;
        onRefreshed(newToken);

        if (!newToken) {
          redirectToLogin();
          return Promise.reject(buildApiError(error));
        }

        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return instance(originalRequest);
      }

      if (error.response?.status === 401 && isAuthEndpoint) {
        // A 401 on login/refresh/register itself means the session truly
        // failed — clean up rather than looping.
        clearTokens();
      }

      return Promise.reject(buildApiError(error));
    },
  );
}

function buildApiError(error: AxiosError<ApiEnvelope<unknown>>): ApiError {
  const envelope = error.response?.data;
  return {
    message: envelope?.message ?? error.message ?? 'An unexpected error occurred.',
    statusCode: error.response?.status,
    requestId: envelope?.request_id,
    errors: envelope?.errors ?? null,
  };
}
