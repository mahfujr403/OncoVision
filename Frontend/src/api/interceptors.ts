import type {
  AxiosInstance,
  InternalAxiosRequestConfig,
  AxiosResponse,
  AxiosError,
} from 'axios';
import type { ApiResponse, RefreshResponseData } from '@/types';
import { API_ENDPOINTS } from '@/constants/api';

// ── Token storage ─────────────────────────────────────────────────────────────
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

// ── Normalised error shape ────────────────────────────────────────────────────
export interface NormalisedApiError {
  message: string;
  statusCode?: number;
  errors?: unknown;
}

// ── Refresh queue — prevents duplicate concurrent refresh calls ───────────────
let isRefreshing = false;
let pendingQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processPendingQueue(error: unknown, token: string | null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (token) resolve(token);
    else reject(error);
  });
  pendingQueue = [];
}

function normaliseAxiosError(
  error: AxiosError<ApiResponse<null>>,
): NormalisedApiError {
  return {
    message:
      error.response?.data?.message ??
      error.message ??
      'An unexpected error occurred.',
    statusCode: error.response?.status,
    errors: error.response?.data?.errors ?? null,
  };
}

// ── Interceptor setup ─────────────────────────────────────────────────────────
export function setupInterceptors(instance: AxiosInstance): void {
  // Attach Bearer token to every outgoing request
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

  // On 401: attempt a single token refresh; queue any concurrent 401 requests
  instance.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error: AxiosError<ApiResponse<null>>) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & {
        _retry?: boolean;
      };

      const isRefreshEndpoint = originalRequest?.url?.includes(
        API_ENDPOINTS.AUTH.REFRESH,
      );

      if (
        error.response?.status === 401 &&
        !originalRequest._retry &&
        !isRefreshEndpoint
      ) {
        originalRequest._retry = true;

        if (isRefreshing) {
          // Queue request — it will retry once refresh completes
          return new Promise<AxiosResponse>((resolve, reject) => {
            pendingQueue.push({
              resolve: (token) => {
                if (originalRequest.headers) {
                  originalRequest.headers.Authorization = `Bearer ${token}`;
                }
                resolve(instance(originalRequest));
              },
              reject,
            });
          });
        }

        isRefreshing = true;
        const storedRefresh = getRefreshToken();

        if (!storedRefresh) {
          isRefreshing = false;
          clearTokens();
          window.location.href = '/login';
          return Promise.reject(normaliseAxiosError(error));
        }

        try {
          const res = await instance.post<ApiResponse<RefreshResponseData>>(
            API_ENDPOINTS.AUTH.REFRESH,
            { refresh_token: storedRefresh },
          );

          const tokens = res.data.data!;
          setTokens(tokens.access_token, tokens.refresh_token);
          isRefreshing = false;
          processPendingQueue(null, tokens.access_token);

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`;
          }
          return instance(originalRequest);
        } catch (refreshErr) {
          isRefreshing = false;
          processPendingQueue(refreshErr, null);
          clearTokens();
          window.location.href = '/login';
          return Promise.reject(refreshErr);
        }
      }

      return Promise.reject(normaliseAxiosError(error));
    },
  );
}
