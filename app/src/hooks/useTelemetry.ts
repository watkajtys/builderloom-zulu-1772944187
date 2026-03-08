import { useQuery } from '@tanstack/react-query';
import PocketBase from 'pocketbase';

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

const fetchTelemetryData = async (): Promise<TelemetryData> => {
  const pb = new PocketBase(window.location.protocol + "//" + window.location.hostname + ":8090");
  try {
     const record = await pb.collection('telemetry_state').getFirstListItem('');
     return {
        version: record.version,
        logs: record.logs || []
     };
  } catch(pbErr) {
     console.log("PB fetch failed, trying Python backend via 8080 or local proxy...", pbErr);
  }

  try {
      const res = await fetch('http://127.0.0.1:8080/state?_t=' + new Date().getTime()); // Loom Python backend
      if (res.ok) {
          const data = await res.json();
          return {
              version: data.version || 'v1.1',
              logs: data.logs || []
          };
      }
  } catch(e) {}
  
  try {
      // Fallback for UI visualization offline testing
      const mockRes = await fetch('/session_state.json', { cache: 'no-store' });
      if (mockRes.ok) {
          const MockData = await mockRes.json();
          return {
              version: MockData.version || 'v1.1 (Mock Offline)',
              logs: MockData.logs || []
          };
      }
  } catch(e) {}

  throw new Error("Cannot fetch telemetry data. PocketBase collection not found and Python backend unreachable.");
};

export const useTelemetry = () => {
  return useQuery<TelemetryData, Error>({
    queryKey: ['telemetry'],
    queryFn: fetchTelemetryData,
    refetchInterval: 5000,
  });
};
