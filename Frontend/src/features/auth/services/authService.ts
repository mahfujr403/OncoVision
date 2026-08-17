// Real backend auth service — all calls go through the shared axiosInstance.
// The mock localStorage simulation has been removed.
import { axiosInstance } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type {
  ApiResponse,
  User,
  LoginResponseData,
  RegisterResponseData,
  RefreshResponseData,
} from '@/types';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

export const authService = {
  async login(payload: LoginPayload): Promise<LoginResponseData> {
    const res = await axiosInstance.post<ApiResponse<LoginResponseData>>(
      API_ENDPOINTS.AUTH.LOGIN,
      payload,
    );
    return res.data.data!;
  },

  async register(payload: RegisterPayload): Promise<RegisterResponseData> {
    const res = await axiosInstance.post<ApiResponse<RegisterResponseData>>(
      API_ENDPOINTS.AUTH.REGISTER,
      payload,
    );
    return res.data.data!;
  },

  async getMe(): Promise<User> {
    const res = await axiosInstance.get<ApiResponse<{ user: User }>>(
      API_ENDPOINTS.AUTH.ME,
    );
    return res.data.data!.user;
  },

  async refresh(refreshToken: string): Promise<RefreshResponseData> {
    const res = await axiosInstance.post<ApiResponse<RefreshResponseData>>(
      API_ENDPOINTS.AUTH.REFRESH,
      { refresh_token: refreshToken },
    );
    return res.data.data!;
  },

  async logout(refreshToken: string): Promise<void> {
    await axiosInstance.post<ApiResponse<null>>(API_ENDPOINTS.AUTH.LOGOUT, {
      refresh_token: refreshToken,
    });
  },

  async logoutAll(): Promise<void> {
    await axiosInstance.post<ApiResponse<null>>(API_ENDPOINTS.AUTH.LOGOUT_ALL);
  },
};
