export interface AgentStatus {
  agentId: string;
  state: 'idle' | 'coding' | 'reflecting' | 'error' | 'initializing';
  currentTask?: string;
  happinessScore: number;
}
