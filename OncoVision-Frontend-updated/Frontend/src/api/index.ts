import { axiosInstance } from './axios-instance';
import { setupInterceptors } from './interceptors';
import type { ApiEnvelope } from '@/types';

setupInterceptors(axiosInstance);

export { axiosInstance };
export * from './interceptors';

/**
 * Every backend response is wrapped in the standard envelope
 * (success/message/data/errors/request_id/timestamp). Services call this
 * to pull out `data` instead of re-implementing the unwrap each time.
 * Throws if the backend reports success: false or data is missing, so
 * callers can rely on a non-null return.
 */
export function unwrap<T>(envelope: ApiEnvelope<T>): T {
  if (!envelope.success || envelope.data === null || envelope.data === undefined) {
    throw {
      message: envelope.message ?? 'Request did not return data.',
      requestId: envelope.request_id,
      errors: envelope.errors ?? null,
    };
  }
  return envelope.data;
}
