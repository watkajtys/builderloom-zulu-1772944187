import { useQuery } from '@tanstack/react-query';
import { executionQueryOptions } from './useOrchestration';

export function useAgents() {
  return useQuery({
    ...executionQueryOptions,
    select: (state) => state.uiAgents,
  });
}
