import { axiosInstance } from './axios-instance';
import { setupInterceptors } from './interceptors';

setupInterceptors(axiosInstance);

export { axiosInstance };
export * from './interceptors';
