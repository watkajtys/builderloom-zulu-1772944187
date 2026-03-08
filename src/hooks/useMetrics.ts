import { useQuery } from '@tanstack/react-query';
import { executionQueryOptions } from './useOrchestration';

export function useMetrics() {
  return useQuery({
    ...executionQueryOptions,
    select: (state) => state.uiMetrics,
  });
}
