export interface AttemptRecord {
  attemptNumber: number;
  promptUsed: string;
  appScreenshotPath?: string | null;
  julesPatchPath?: string | null;
  julesUrl?: string | null;
  julesAction?: string | null;
  score: number;
  critique: string;
}

export interface LoopIteration {
  id: number;
  timestamp: string;
  goal: string;
  targetRoute: string;
  dataModel?: string | null;
  requiresDesign: boolean;
  testScenario?: string | null;
  negativeHistory: string[];
  brainstormingOutput?: string | null;
  baseBriefs: string[];
  baseSeedPaths: (string | null)[];
  baseVariantsData?: Record<string, unknown>[] | null;
  seedReviewCritique?: string | null;
  designScreenshotPath?: string | null;
  designVariantsPaths: (string | null)[];
  layoutReviewCritique?: string | null;
  chosenDesignPath?: string | null;
  designReviewCritique?: string | null;
  themeVariantsPaths: (string | null)[];
  chosenThemePath?: string | null;
  themeReviewCritique?: string | null;
  attempts: AttemptRecord[];
  happinessScore: number;
  successfulBranch?: string | null;
  abandoned: boolean;
  architecturalCritique?: string | null;
  reflectionLearnings?: string | null;
  gitCommit?: string | null;
}
