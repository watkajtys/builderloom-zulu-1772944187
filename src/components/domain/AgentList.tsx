import { AgentStatus } from '../../types/agents';
import AgentCard from './AgentCard';
import CompactAgentCard from './CompactAgentCard';

interface AgentListProps {
  agents: AgentStatus[];
  compact?: boolean;
}

export default function AgentList({ agents, compact = false }: AgentListProps) {
  if (compact) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">Active Agents</h2>
        </div>
        <div className="p-0">
          <ul className="divide-y divide-slate-800">
            {agents.map((agent) => (
              <CompactAgentCard key={agent.agentId} agent={agent} />
            ))}
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      <div className="p-0">
        <ul className="divide-y divide-slate-800">
          {agents.map((agent) => (
            <AgentCard key={agent.agentId} agent={agent} />
          ))}
        </ul>
      </div>
    </div>
  );
}
