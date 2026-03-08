import React from 'react';

export default function Header() {
  return (
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
  );
}
