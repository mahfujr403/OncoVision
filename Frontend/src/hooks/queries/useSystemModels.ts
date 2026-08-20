import { useQuery } from '@tanstack/react-query';
import { fetchRegisteredModels } from '@/api/services/systemService';
import { QUERY_KEYS } from '@/constants/api';
import { STALE_TIME_MS } from '@/constants/app';

export function useSystemModels() {
  return useQuery({
    queryKey: QUERY_KEYS.SYSTEM_MODELS,
    queryFn: fetchRegisteredModels,
    staleTime: STALE_TIME_MS,
  });
}
