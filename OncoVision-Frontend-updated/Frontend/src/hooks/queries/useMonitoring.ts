import { useQuery } from '@tanstack/react-query';
import { fetchMonitoringStatus } from '@/api/services/monitoringService';
import { QUERY_KEYS } from '@/constants/api';

export function useMonitoring() {
  return useQuery({
    queryKey: QUERY_KEYS.MONITORING,
    queryFn: fetchMonitoringStatus,
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}
