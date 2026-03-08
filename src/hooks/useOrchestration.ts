import { useQuery } from '@tanstack/react-query';
import { fetchProductState, fetchExecutionState } from '../services/api';

export const productQueryOptions = {
  queryKey: ['productState'],
  queryFn: fetchProductState,
  refetchInterval: 5000,
};

export const executionQueryOptions = {
  queryKey: ['executionState'],
  queryFn: fetchExecutionState,
  refetchInterval: 5000,
};
