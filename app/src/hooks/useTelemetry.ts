import { useQuery } from '@tanstack/react-query';
import { TelemetryData } from '../types/telemetry';
import { apiClient } from '../api/client';

export const useTelemetry = () => {
  return useQuery<TelemetryData, Error>({
    queryKey: ['telemetry'],
    queryFn: () => apiClient.fetchTelemetryData(),
    refetchInterval: 5000,
  });
};
