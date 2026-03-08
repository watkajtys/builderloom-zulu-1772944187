import { useQuery } from '@tanstack/react-query';
import { executionQueryOptions } from './useOrchestration';

export function useContainers() {
  return useQuery({
    ...executionQueryOptions,
    select: (state) => state.uiContainers,
  });
}
