import { axiosInstance, unwrap } from '@/api';
import { API_ENDPOINTS } from '@/constants/api';
import type { ApiEnvelope, ModelRegistryResponse, ModelRuntimeStatusList, SystemInfo } from '@/types';

// These four endpoints have no `response_model` on /system and /system/runtime
// (verified in app/api/v1/system.py) — treat those two payloads as opaque
// and render them generically. /system/models DOES have a concrete shape
// (ModelRegistryResponse, from app/ml/metadata/metadata_service.py) and is
// typed accordingly below.

export async function fetchSystemInfo(): Promise<SystemInfo> {
  const response = await axiosInstance.get<ApiEnvelope<SystemInfo>>(API_ENDPOINTS.SYSTEM.INFO);
  return unwrap(response.data);
}

export async function fetchRegisteredModels(): Promise<ModelRegistryResponse> {
  const response = await axiosInstance.get<ApiEnvelope<ModelRegistryResponse>>(API_ENDPOINTS.SYSTEM.MODELS);
  return unwrap(response.data);
}

export async function fetchRuntimeHealth(): Promise<Record<string, unknown>> {
  const response = await axiosInstance.get<ApiEnvelope<Record<string, unknown>>>(API_ENDPOINTS.SYSTEM.RUNTIME);
  return unwrap(response.data);
}

export async function fetchModelRuntimeStatus(): Promise<ModelRuntimeStatusList> {
  const response = await axiosInstance.get<ApiEnvelope<ModelRuntimeStatusList>>(API_ENDPOINTS.SYSTEM.MODELS_STATUS);
  return unwrap(response.data);
}
