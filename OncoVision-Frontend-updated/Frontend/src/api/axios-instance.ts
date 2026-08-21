import axios, { type AxiosInstance } from 'axios';
import { API_BASE_URL } from '@/constants/api';

export const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});
