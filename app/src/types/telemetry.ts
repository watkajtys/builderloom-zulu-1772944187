export interface TelemetryLog {
  id: string;
  timestamp: string;
  agent: string;
  level: string;
  message: string;
  metadata?: any;
}

export interface TelemetryData {
  version: string;
  logs: TelemetryLog[];
}
