export interface DockerContainer {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'crashed' | 'starting';
  image: string;
  ports: string[];
}

export interface OrchestrationMetrics {
  activeContainers: number;
  agentCount: number;
  systemHealth: number; // 0-100
}
