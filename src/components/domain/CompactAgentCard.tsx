import { AgentStatus } from '../../types/agents';
import { Users } from 'lucide-react';

interface CompactAgentCardProps {
  agent: AgentStatus;
}

export default function CompactAgentCard({ agent }: CompactAgentCardProps) {
  return (
    <li className="p-4 hover:bg-slate-800/50 transition-colors flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
            <Users size={16} />
          </div>
          <span className="font-mono text-sm text-slate-200">{agent.agentId}</span>
        </div>
        <span className="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
          Score: {agent.happinessScore}
        </span>
      </div>
      <div className="bg-slate-950 p-3 rounded border border-slate-800 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">Status</span>
          <span className="text-xs font-mono text-fuchsia-400 flex items-center gap-2">
            {agent.state === 'coding' && <span className="w-1.5 h-1.5 rounded-full bg-fuchsia-400 animate-pulse"></span>}
            {agent.state}
          </span>
        </div>
        {agent.currentTask && (
          <div className="border-l-2 border-slate-700 pl-3">
            <p className="text-xs text-slate-400 font-mono italic">"{agent.currentTask}"</p>
          </div>
        )}
      </div>
    </li>
  );
}
