export interface BacklogTask {
  id: string;
  type: 'feature' | 'refactor' | 'bugfix';
  priority: number;
  description: string;
  targetRoute: string;
  dataModel?: string | null;
  requiresDesign: boolean;
  testScenario: string;
  context: string;
  status: string;
}
