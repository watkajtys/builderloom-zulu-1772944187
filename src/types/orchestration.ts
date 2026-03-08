import { DockerContainer, OrchestrationMetrics } from './infrastructure';
import { AgentStatus } from './agents';
import { BacklogTask } from './tasks';
import { LoopIteration } from './iteration';

export interface ProductState {
  schemaVersion: string;
  projectName: string;
  appMeta: string;
  productPhase: string;
  productRoadmap: string;
  repoMemory: Record<string, unknown>;
  currentIteration: number;
  activeBranch: string;
  
  backlog: BacklogTask[];
  activeTaskId: string | null;
  
  inspirationGoal: string;
  inspirationTargetRoute: string;
  inspirationDataModel: string | null;
  inspirationRequiresDesign: boolean;
  inspirationMode: string;
  inspirationTestScenario: string;
  
  history: LoopIteration[];
  stitchProjectId: string | null;
  stitchScreenId: string | null;
  activeJulesPrompt: string | null;
  activeJulesUrl: string | null;
  activeJulesAction: string | null;
  currentStatus: string;
  currentPhase: string;
  pendingSteer: string[];
  steeringHistory: Record<string, unknown>[];
  liveLogs: string[];
  shutdownRequested: boolean;
  updateScheduled: boolean;
  dbStats: Record<string, number>;
}

export interface ExecutionState {
  schemaVersion: string;
  uiContainers: DockerContainer[];
  uiAgents: AgentStatus[];
  uiMetrics: OrchestrationMetrics;
}

export type SessionState = ProductState & ExecutionState;
