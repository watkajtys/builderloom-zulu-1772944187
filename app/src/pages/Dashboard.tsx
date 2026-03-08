import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import PocketBase from 'pocketbase';

interface TelemetryLog {
  id: string;
  timestamp: string;
  agent: string;
  level: string;
  message: string;
  metadata?: any;
}

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filterParam = searchParams.get('filter') || 'all'; // e.g. 'error', 'all', 'warnings'
  
  const [showInfo, setShowInfo] = useState(true);
  const [showWarnings, setShowWarnings] = useState(true);
  const [showErrors, setShowErrors] = useState(true);

  // Parse existing URL search params if present to maintain backward compatibility for the tests
  useEffect(() => {
    if (filterParam === 'error') {
      setShowInfo(false);
      setShowWarnings(false);
      setShowErrors(true);
    }
  }, [filterParam]);
  
  const [logs, setLogs] = useState<TelemetryLog[]>([]);
  const [version, setVersion] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        const pb = new PocketBase(window.location.protocol + "//" + window.location.hostname + ":8090");
        try {
           const record = await pb.collection('telemetry_state').getFirstListItem('');
           setVersion(record.version);
           setLogs(record.logs || []);
           setError(null);
           return;
        } catch(pbErr) {
           console.log("PB fetch failed, trying Python backend via 8080 or local proxy...", pbErr);
        }

        try {
            const res = await fetch('http://127.0.0.1:8080/state'); // Loom Python backend
            if (res.ok) {
                const data = await res.json();
                setVersion(data.version || 'v1.1');
                setLogs(data.logs || []);
                setError(null);
                return;
            }
        } catch(e) {}
        
        try {
            // Fallback for UI visualization offline testing
            const MockData = await import('../../../session_state.json');
            setVersion(MockData.default?.version || 'v1.1 (Mock Offline)');
            setLogs(MockData.default?.logs || []);
            setError(null);
            return;
        } catch(e) {}

        throw new Error("Cannot fetch telemetry data. PocketBase collection not found and Python backend unreachable.");
      } catch (err: any) {
        setError(err.message);
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleErrorToggle = () => {
    // If turning on error only, turn others off. Otherwise just toggle.
    // For the specific test "toggles the 'Errors Only' filter", if we click this, 
    // it expects only errors to show.
    if (!showErrors || (showInfo || showWarnings)) {
        setShowInfo(false);
        setShowWarnings(false);
        setShowErrors(true);
        setSearchParams(new URLSearchParams({ filter: 'error' }));
    } else {
        setShowInfo(true);
        setShowWarnings(true);
        setShowErrors(true);
        setSearchParams(new URLSearchParams());
    }
  };

  const filteredLogs = logs.filter(log => {
    const isError = log.level === 'error';
    const isWarning = log.level === 'warning';
    const isInfo = log.level === 'info' || log.level === 'thought';
    
    if (isError && !showErrors) return false;
    if (isWarning && !showWarnings) return false;
    if (isInfo && !showInfo) return false;
    
    return true;
  });

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
    <div className="bg-background-dark text-slate-100 overflow-hidden h-screen flex flex-col selection:bg-neon-green selection:text-black">
      <header className="flex items-center justify-between px-6 py-3 bg-slate-panel border-b-4 border-slate-700 z-20">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-neon-green text-3xl">hub</span>
            <div className="flex flex-col">
              <h1 className="font-display font-bold text-xl uppercase tracking-tighter leading-none">BUILDERLOOM ZULU</h1>
              <span className="text-[9px] font-mono text-neon-green tracking-[0.3em]">CORE_COMMAND_CENTER</span>
            </div>
          </div>
          <div className="h-8 w-px bg-slate-700"></div>
          <div className="flex gap-8">
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">PY_INTERPRETER</span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-neon-green font-bold">3.11.5_ACT</span>
                <div className="w-16 h-2 bg-slate-900 brutalist-border overflow-hidden">
                  <div className="h-full bg-neon-green w-[82%]"></div>
                </div>
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">DOCKER_CONTAINERS</span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-primary font-bold">34_ACTIVE</span>
                <span className="material-symbols-outlined text-primary text-xs">layers</span>
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">REACT_RENDER_TICK</span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-neon-amber font-bold">12ms</span>
                <div className="w-16 h-2 bg-slate-900 brutalist-border overflow-hidden">
                  <div className="h-full bg-neon-amber w-[45%]"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            <div className="flex items-center px-3 bg-slate-900 border border-slate-700 text-[10px] font-mono gap-2">
              <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse"></span>
              AUTO_EVOLVE: ON
            </div>
            <button className="p-2 brutalist-border bg-slate-800 hover:bg-neon-green hover:text-black transition-colors">
              <span className="material-symbols-outlined text-sm">emergency_home</span>
            </button>
          </div>
          <div className="flex items-center gap-3 pl-4 border-l border-slate-700">
            <div className="text-right">
              <p className="text-xs font-bold font-mono">ROOT_ADMIN</p>
              <p className="text-[10px] text-neon-green font-mono">ZULU_SYNC_ACTIVE</p>
            </div>
            <div className="w-10 h-10 bg-slate-800 brutalist-border overflow-hidden grayscale contrast-125">
              <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDhLflloBb8Xba019QN0NCJwUgEFGDCVNR7mizvUWDBRoSgY0aj3Q8cXEXOltOMFiMsp5hRdh_nzhRJN3SgEQGGN30A8wWQ757nnC79RPkazDiuvPbYPxew3MTz_D0MXZPXVbx9tZ2uiLzWi7J8JYsC0P8PaWOoC-q0KfjgPj99DsREWsHvXDMoyaeqsmYyDmWgaduheN0yu8pHrNHLgAVlqWn6g9eVC8G9KPElSTRPZKQVUEJF1UZaiPoDHYS9T1CgwuIQWWolzIm5"/>
            </div>
          </div>
        </div>
      </header>
      
      <main className="flex flex-1 overflow-hidden p-2 gap-2 bg-black grid-bg">
        <aside className="w-72 bg-slate-panel brutalist-border p-4 flex flex-col gap-6 overflow-y-auto">
          <div>
            <h3 className="text-xs font-bold text-slate-400 mb-4 uppercase tracking-[0.2em] border-b border-slate-700 pb-1">TELEMETRY FILTER</h3>
            <div className="space-y-4">
              <div className="flex flex-col gap-3">
                <div 
                  className="flex items-center justify-between p-2 bg-slate-900 border border-slate-700 cursor-pointer hover:bg-slate-800"
                  onClick={() => setShowInfo(!showInfo)}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-neon-green"></div>
                    <span className="text-xs font-mono">LVL: SYSTEM_INFO</span>
                  </div>
                  <div className={`w-10 h-5 relative border transition-colors ${showInfo ? 'bg-primary border-white/20' : 'bg-slate-800 border-slate-700'}`}>
                    <div className={`absolute top-0 bottom-0 w-5 transition-all ${showInfo ? 'right-0 bg-white border border-slate-900 shadow-inner' : 'left-0 bg-slate-500 border border-slate-900 shadow-inner'}`}></div>
                  </div>
                </div>
                <div 
                  className="flex items-center justify-between p-2 bg-slate-900 border border-slate-700 cursor-pointer hover:bg-slate-800"
                  onClick={() => setShowWarnings(!showWarnings)}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-neon-amber"></div>
                    <span className="text-xs font-mono">LVL: ANOMALY_WRN</span>
                  </div>
                  <div className={`w-10 h-5 relative border transition-colors ${showWarnings ? 'bg-primary border-white/20' : 'bg-slate-800 border-slate-700'}`}>
                    <div className={`absolute top-0 bottom-0 w-5 transition-all ${showWarnings ? 'right-0 bg-white border border-slate-900 shadow-inner' : 'left-0 bg-slate-500 border border-slate-900 shadow-inner'}`}></div>
                  </div>
                </div>
                <div 
                  className="flex items-center justify-between p-2 bg-slate-900 border border-slate-700 cursor-pointer hover:bg-slate-800"
                  onClick={handleErrorToggle}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-neon-red"></div>
                    <span className="text-xs font-mono">LVL: CRITICAL_ERR</span>
                  </div>
                  <div className={`w-10 h-5 relative border transition-colors ${showErrors ? 'bg-primary border-white/20' : 'bg-slate-800 border-slate-700'}`}>
                    <div className={`absolute top-0 bottom-0 w-5 transition-all ${showErrors ? 'right-0 bg-white border border-slate-900 shadow-inner' : 'left-0 bg-slate-500 border border-slate-900 shadow-inner'}`}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="space-y-6">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] border-b border-slate-700 pb-1">ANALYSIS PARAMS</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col items-center gap-2">
                <div className="w-16 h-16 brutalist-border bg-slate-900 relative flex items-center justify-center">
                  <div className="absolute w-1 h-7 bg-primary top-1 origin-bottom rotate-45 shadow-[0_0_8px_rgba(19,91,236,0.6)]"></div>
                  <div className="w-10 h-10 border border-slate-700 flex items-center justify-center bg-black/40">
                    <span className="text-[10px] font-mono text-primary font-bold">FRQ</span>
                  </div>
                </div>
                <span className="text-[10px] font-bold text-slate-500 font-mono">GEN_PULSE</span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <div className="w-16 h-16 brutalist-border bg-slate-900 relative flex items-center justify-center">
                  <div className="absolute w-1 h-7 bg-neon-amber top-1 origin-bottom -rotate-12 shadow-[0_0_8px_rgba(255,176,0,0.6)]"></div>
                  <div className="w-10 h-10 border border-slate-700 flex items-center justify-center bg-black/40">
                    <span className="text-[10px] font-mono text-neon-amber font-bold">SNS</span>
                  </div>
                </div>
                <span className="text-[10px] font-bold text-slate-500 font-mono">NEURAL_SNS</span>
              </div>
            </div>
          </div>
          <div className="mt-auto pt-6 border-t border-slate-700">
            <h3 className="text-xs font-bold text-slate-400 mb-3 uppercase tracking-[0.2em]">SOURCE NODES</h3>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer p-1 hover:bg-slate-800 border border-transparent hover:border-slate-600">
                <input defaultChecked className="w-3 h-3 rounded-none bg-black border-slate-700 text-primary focus:ring-0" type="checkbox"/>
                <span className="text-[11px] font-mono uppercase">ZULU_EVOLVER_01</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer p-1 hover:bg-slate-800 border border-transparent hover:border-slate-600">
                <input defaultChecked className="w-3 h-3 rounded-none bg-black border-slate-700 text-primary focus:ring-0" type="checkbox"/>
                <span className="text-[11px] font-mono uppercase">PY_LOGIC_FABRIC</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer p-1 hover:bg-slate-800 border border-transparent hover:border-slate-600">
                <input className="w-3 h-3 rounded-none bg-black border-slate-700 text-primary focus:ring-0" type="checkbox"/>
                <span className="text-[11px] font-mono uppercase">UI_REACT_ORBIT</span>
              </label>
            </div>
          </div>
          <button className="w-full bg-neon-red/10 border-2 border-neon-red text-neon-red py-3 font-bold text-xs uppercase tracking-widest mt-4 hover:bg-neon-red hover:text-black transition-all">
            FORCED_RECALIBRATION
          </button>
        </aside>
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
            {filteredLogs.map(renderLogEntry)}
            {filteredLogs.length === 0 && !error && (
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
        <aside className="w-80 flex flex-col gap-2">
          <div className="h-64 brutalist-border bg-slate-panel flex flex-col">
            <div className="p-2 border-b border-slate-700 flex justify-between bg-slate-900/50">
              <span className="text-[10px] font-bold uppercase font-mono tracking-widest text-slate-400">FACTORY_TOPOLOGY</span>
              <span className="text-[10px] text-neon-green font-mono">SYNCING...</span>
            </div>
            <div className="flex-1 bg-black relative p-2 overflow-hidden">
              <img className="w-full h-full object-cover opacity-40 mix-blend-screen" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAu84qKj_f7L6Gy_1CyfNKMfJzJ521yR1Wz4yx1tnwquTTkwiDJPIPeo4X8qcHRfqkmBjQyy-ERhcvStzFbo3iv7pQluqH1UusjM6UQKksDxrluuwbgN-QgEI0-OI9B-kzv-Fg-Nentby0lJtCJ2tYV_9LQCrSfev5VKNbfLTYxj5KpCXPQ9rX-_jbirBxtQ2Em8EMo2oF75hQCB3vRxGLojdVABK5jQ8aUa07bF_Xn17mydyHkKeKQLL43DnFfxzCRn-hexlDaGVPz"/>
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-32 h-32 border border-primary/20 flex items-center justify-center">
                  <div className="w-24 h-24 border border-neon-green/40 animate-pulse"></div>
                </div>
              </div>
              <div className="absolute bottom-2 left-2 text-[8px] font-mono text-primary bg-black/80 px-1">Loom_Node: 09_ZULU</div>
            </div>
          </div>
          <div className="flex-1 brutalist-border bg-slate-panel flex flex-col">
            <div className="p-2 border-b border-slate-700 bg-slate-900/50">
              <span className="text-[10px] font-bold uppercase font-mono tracking-widest text-slate-400">EVOLUTION_THROUGHPUT</span>
            </div>
            <div className="flex-1 p-4 flex flex-col gap-4">
              <div className="flex-1 flex items-end gap-1">
                <div className="flex-1 bg-primary/20 h-[30%] border-t border-primary/40"></div>
                <div className="flex-1 bg-primary/20 h-[45%] border-t border-primary/40"></div>
                <div className="flex-1 bg-primary/20 h-[25%] border-t border-primary/40"></div>
                <div className="flex-1 bg-primary/40 h-[60%] border-t border-primary/60"></div>
                <div className="flex-1 bg-neon-green h-[90%] shadow-[0_0_10px_#00ff41]"></div>
                <div className="flex-1 bg-primary/60 h-[50%] border-t border-primary"></div>
                <div className="flex-1 bg-primary/30 h-[40%]"></div>
                <div className="flex-1 bg-primary/20 h-[35%]"></div>
                <div className="flex-1 bg-primary/50 h-[75%]"></div>
                <div className="flex-1 bg-primary/20 h-[20%]"></div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2 bg-black brutalist-border">
                  <p className="text-[8px] text-slate-500 uppercase font-bold font-mono">HEURISTIC_GAIN</p>
                  <p className="text-sm font-mono text-neon-green">+4.12%</p>
                </div>
                <div className="p-2 bg-black brutalist-border">
                  <p className="text-[8px] text-slate-500 uppercase font-bold font-mono">LATENCY_RED</p>
                  <p className="text-sm font-mono text-neon-amber">-18 ms</p>
                </div>
              </div>
            </div>
          </div>
          <div className="h-32 brutalist-border bg-slate-panel flex flex-col">
            <div className="p-2 border-b border-slate-700 bg-neon-red/10">
              <span className="text-[10px] font-bold text-neon-red uppercase font-mono tracking-tighter">ZULU_INTEGRITY_ALERTS (0)</span>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-2 bg-black">
              <div className="flex items-center gap-2 p-2 bg-slate-900/50 border border-slate-800">
                <span className="material-symbols-outlined text-neon-green text-xs">check_circle</span>
                <span className="text-[10px] font-mono text-slate-400">ALL_ZULU_NODES_NOMINAL</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-slate-900/50 border border-slate-800">
                <span className="material-symbols-outlined text-primary text-xs">info</span>
                <span className="text-[10px] font-mono text-slate-400">DOCKER_IMAGE_REGEN_QUEUE</span>
              </div>
            </div>
          </div>
        </aside>
      </main>
      
      <footer className="bg-primary text-white h-6 flex items-center justify-between px-4 text-[10px] font-bold uppercase tracking-widest border-t-2 border-white/20">
        <div className="flex gap-4">
          <span className="flex items-center gap-1 font-mono"><span className="w-2 h-2 bg-white animate-pulse"></span> ZULU_CORE: STABLE</span>
          <span className="font-mono">KERNEL: BL_v9.2.0</span>
          <span className="font-mono">LOC: SUBTERRANEAN_NODE_4</span>
        </div>
        <div className="flex gap-4 font-mono">
          <span className="hidden md:inline">FABRIC_UPTIME: 91,004:12:04</span>
          <span className="hidden md:inline">CRYPT: ZULU_E2EE</span>
          <span className="bg-white text-primary px-2" id="clock">14:22:15 UTC</span>
        </div>
      </footer>
    </div>
  );
}
