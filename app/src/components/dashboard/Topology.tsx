import React from 'react';

export default function Topology() {
  return (
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
  );
}
