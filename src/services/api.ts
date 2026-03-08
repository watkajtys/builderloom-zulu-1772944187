import { SessionState, ProductState, ExecutionState } from '../types/orchestration';

const toCamelCase = (str: string) => str.replace(/_([a-z])/g, (g) => g[1].toUpperCase());

const convertKeysToCamelCase = (obj: unknown): unknown => {
  if (Array.isArray(obj)) {
    return obj.map(v => convertKeysToCamelCase(v));
  } else if (obj !== null && obj.constructor === Object) {
    return Object.keys(obj as Record<string, unknown>).reduce((result, key) => {
      result[toCamelCase(key)] = convertKeysToCamelCase((obj as Record<string, unknown>)[key]);
      return result;
    }, {} as Record<string, unknown>);
  }
  return obj;
};

export const fetchProductState = async (): Promise<ProductState> => {
  const response = await fetch('/api/session_state');
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data = await response.json();
  return convertKeysToCamelCase(data) as ProductState;
};

export const fetchExecutionState = async (): Promise<ExecutionState> => {
  const response = await fetch('/api/execution_state');
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data = await response.json();
  return convertKeysToCamelCase(data) as ExecutionState;
};

export const fetchState = async (): Promise<SessionState> => {
  const [productState, executionState] = await Promise.all([
    fetchProductState(),
    fetchExecutionState()
  ]);
  
  return { ...productState, ...executionState } as SessionState;
};
