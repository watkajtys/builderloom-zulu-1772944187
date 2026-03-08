import { DockerContainer } from '../../types/infrastructure';

interface ContainerListProps {
  containers: DockerContainer[];
}

export default function ContainerList({ containers }: ContainerListProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Container Infrastructure</h2>
        <span className="px-2 py-1 rounded text-[10px] font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20">
          {containers.length} nodes
        </span>
      </div>
      <div className="p-0">
        <ul className="divide-y divide-slate-800">
          {containers.map((container) => (
            <li key={container.id} className="p-4 hover:bg-slate-800/50 transition-colors flex items-center justify-between group">
              <div className="flex items-center gap-4">
                <div className={`w-2 h-2 rounded-full shadow-[0_0_10px_currentColor] ${container.status === 'running' ? 'bg-emerald-400 text-emerald-400' : 'bg-red-400 text-red-400'}`}></div>
                <div>
                  <p className="font-mono text-sm text-slate-200">{container.name}</p>
                  <p className="text-xs text-slate-500 font-mono mt-1">{container.image}</p>
                </div>
              </div>
              <div className="text-right flex flex-col items-end gap-1">
                <span className={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded ${container.status === 'running' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                  {container.status}
                </span>
                <span className="text-xs text-slate-600 font-mono">{container.ports.join(', ')}</span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
