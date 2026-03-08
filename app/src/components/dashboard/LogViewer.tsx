

import { TelemetryLog } from '../../types/telemetry';

interface LogViewerProps {
  logs: TelemetryLog[];
  error: string | null;
}

export default function LogViewer({ logs, error }: LogViewerProps) {
  const renderLogEntry = (log: TelemetryLog) => {
    const isError = log.level === 'error';
    const isWarning = log.level === 'warning';
    
    // We parse timestamp for T+04:12 format just as visual flair if we want, 
    // or just display actual time. We'll stick to a standard T+ formatting for design parity.
    const timeStr = new Date(log.timestamp).toISOString().split('T')[1].slice(0, 12);

    let borderColor = 'border-transparent';
    let textColor = 'text-neon-green';
    let bgColor = 'hover:bg-slate-900/50';
    let label = '[INFO]';
    
    if (isError) {
      borderColor = 'border-neon-red';
      textColor = 'text-neon-red';
      bgColor = 'bg-neon-red/10';
      label = '[HALT!!]';
    } else if (isWarning) {
      borderColor = 'hover:border-neon-amber';
      textColor = 'text-neon-amber';
      label = '[ANOMALY]';
    } else if (log.level === 'thought') {
       textColor = 'text-primary';
       borderColor = 'border-primary';
       bgColor = 'bg-primary/5';
       label = '[THOUGHT]';
    }

    return (
      <div key={log.id} className={`flex gap-4 mb-2 p-1 group border-l-2 ${borderColor} ${bgColor} transition-all`}>
        <span className="text-slate-600 shrink-0">T+{timeStr}</span>
        <span className={`${textColor} shrink-0 font-bold`}>{label}</span>
        <div className="text-slate-100 flex-1">
          <span className="text-slate-500">{"{"}</span>
          <span className="text-primary">"agent"</span><span className="text-slate-500">:</span> <span className="text-neon-amber">"{log.agent}"</span>,{" "}
          <span className="text-primary">"message"</span><span className="text-slate-500">:</span> <span className={`${isError ? 'text-neon-red' : 'text-neon-green'}`}>"{log.message}"</span>
          {log.metadata && Object.keys(log.metadata).length > 0 && (
            <>
              , <span className="text-primary">"metadata"</span><span className="text-slate-500">:</span> <span className="text-neon-amber">{JSON.stringify(log.metadata)}</span>
            </>
          )}
          <span className="text-slate-500">{"}"}</span>
        </div>
      </div>
    );
  };

  return (
    <section className="flex-1 flex flex-col brutalist-border bg-black relative overflow-hidden">
      <div className="scanline"></div>
      <div className="bg-slate-panel p-3 border-b-2 border-slate-700 flex justify-between items-center z-20">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-neon-green text-sm">precision_manufacturing</span>
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-200">ZULU_STRUCTURED_TELEMETRY</span>
          </div>
          <div className="flex gap-2">
            <span className="px-2 py-0.5 bg-neon-green/10 border border-neon-green text-neon-green text-[9px] font-bold">LIVING_FACTORY_OK</span>
            <span className="px-2 py-0.5 bg-slate-900 border border-slate-700 text-slate-500 text-[9px] font-bold">QUEUE: 0.04ms</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-500 uppercase">SYS_CLOCK: [INTERNAL]</span>
          <button className="material-symbols-outlined text-slate-400 hover:text-neon-green text-sm">terminal</button>
          <button className="material-symbols-outlined text-slate-400 hover:text-neon-green text-sm">settings_input_component</button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto log-stream p-4 font-mono text-[13px] leading-relaxed relative bg-[rgba(0,0,0,0.8)]">
        {error && <div className="text-neon-red mb-4 p-2 bg-neon-red/10 border border-neon-red font-bold">ERROR: {error}</div>}
        {logs.map(renderLogEntry)}
        {logs.length === 0 && !error && (
          <div className="text-slate-500 italic">No telemetry data available.</div>
        )}
      </div>
      <div className="bg-slate-900 p-2 border-t-2 border-slate-700 flex gap-2 z-20">
        <span className="text-neon-green font-bold px-2 py-1 font-mono text-sm">ZULU_CLI_&gt;</span>
        <input className="flex-1 bg-black border-none text-neon-green font-mono focus:ring-0 placeholder:text-slate-800 text-sm" placeholder="exec --zulu-core 'rebuild_neural_links' --force" type="text"/>
        <div className="flex gap-1">
          <kbd className="bg-slate-800 border border-slate-700 text-[9px] px-2 py-1 text-slate-500 font-mono">EXECUTE</kbd>
          <kbd className="bg-slate-800 border border-slate-700 text-[9px] px-2 py-1 text-slate-500 font-mono">ENTER</kbd>
        </div>
      </div>
    </section>
  );
}
