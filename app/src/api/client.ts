import PocketBase from 'pocketbase';
import { TelemetryData } from '../types/telemetry';

export class ApiClient {
  private pb: PocketBase;

  constructor() {
    this.pb = new PocketBase(window.location.protocol + "//" + window.location.hostname + ":8090");
  }

  async fetchTelemetryData(): Promise<TelemetryData> {
    try {
      const res = await fetch('http://127.0.0.1:8080/api/session_state?_t=' + new Date().getTime());
      if (res.ok) {
        const data = await res.json();
        return {
          version: data.version || 'v1.1',
          logs: data.logs || []
        };
      }
    } catch (e) {
      console.log("Python API failed, falling back to PocketBase...", e);
    }
    
    try {
      const record = await this.pb.collection('telemetry_state').getFirstListItem('');
      return {
        version: record.version,
        logs: record.logs || []
      };
    } catch (pbErr) {
      console.log("PB fetch failed, trying local proxy...", pbErr);
    }
    
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
    } catch (e) {
      // Ignore
    }

    throw new Error("Cannot fetch telemetry data. PocketBase collection not found and Python backend unreachable.");
  }
}

export const apiClient = new ApiClient();
