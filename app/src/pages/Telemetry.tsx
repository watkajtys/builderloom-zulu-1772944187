import React from 'react';
import { useTelemetry } from '../hooks/useTelemetry';

export default function Telemetry() {
  const { data, error, isLoading: loading } = useTelemetry();
  
  const logs = data?.logs || [];
  const version = data?.version || '';
  const errorMessage = error?.message || null;

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">System Telemetry</h1>
      {version && <p className="text-sm text-gray-400 mb-6">Schema Version: {version}</p>}
      
      {errorMessage && <div className="bg-red-900/50 text-red-200 p-4 rounded mb-6">{errorMessage}</div>}
      
      {loading && logs.length === 0 ? (
        <p>Loading telemetry data...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="p-3 font-semibold text-slate-300">Timestamp</th>
                <th className="p-3 font-semibold text-slate-300">Agent</th>
                <th className="p-3 font-semibold text-slate-300">Level</th>
                <th className="p-3 font-semibold text-slate-300">Message</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                  <td className="p-3 text-sm font-mono text-slate-400">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="p-3 text-sm">
                    <span className="bg-slate-800 px-2 py-1 rounded text-slate-300 capitalize">
                      {log.agent}
                    </span>
                  </td>
                  <td className="p-3 text-sm">
                    <span className={`px-2 py-1 rounded capitalize text-xs font-bold
                      ${log.level === 'error' ? 'bg-red-900/50 text-red-400' : 
                        log.level === 'warning' ? 'bg-yellow-900/50 text-yellow-400' : 
                        'bg-blue-900/50 text-blue-400'}`}
                    >
                      {log.level}
                    </span>
                  </td>
                  <td className="p-3 text-sm text-slate-300">
                    {log.message}
                  </td>
                </tr>
              ))}
              {logs.length === 0 && !errorMessage && (
                <tr>
                  <td colSpan={4} className="p-6 text-center text-slate-500">
                    No telemetry events recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
