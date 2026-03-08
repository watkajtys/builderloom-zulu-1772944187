import React from 'react';

interface SidebarProps {
  showInfo: boolean;
  setShowInfo: (val: boolean) => void;
  showWarnings: boolean;
  setShowWarnings: (val: boolean) => void;
  showErrors: boolean;
  handleErrorToggle: () => void;
}

export default function Sidebar({
  showInfo,
  setShowInfo,
  showWarnings,
  setShowWarnings,
  showErrors,
  handleErrorToggle
}: SidebarProps) {
  return (
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
  );
}
