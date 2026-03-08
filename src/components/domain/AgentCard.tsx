import { AgentStatus } from '../../types/agents';
import { Users } from 'lucide-react';

interface AgentCardProps {
  agent: AgentStatus;
}

export default function AgentCard({ agent }: AgentCardProps) {
  return (
    <li className="p-6 hover:bg-slate-800/50 transition-colors">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500/20 to-fuchsia-500/20 text-fuchsia-400 border border-fuchsia-500/30">
            <Users size={24} />
          </div>
          <div>
            <h3 className="font-mono text-lg font-bold text-slate-200">{agent.agentId}</h3>
            <div className="flex gap-2 mt-1">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-widest uppercase bg-slate-950 text-slate-400 border border-slate-800">
                {agent.state}
              </span>
            </div>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500 uppercase font-mono mb-1">Happiness</p>
          <p className="text-xl font-bold text-emerald-400">{agent.happinessScore}/10</p>
        </div>
      </div>
      
      {agent.currentTask && (
        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
          <p className="text-xs text-slate-500 font-mono mb-2 uppercase tracking-widest">Current Task</p>
          <p className="text-sm text-slate-300 font-mono">
            {agent.currentTask}
          </p>
        </div>
      )}
    </li>
  );
}
