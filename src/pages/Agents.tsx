import { useAgents } from '../hooks/useAgents';
import AgentList from '../components/domain/AgentList';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';

export default function Agents() {
  const { data: agents = [], isLoading, error } = useAgents();

  if (isLoading && !agents.length) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Agent Fleet</h1>
        <p className="text-slate-400 text-sm">Manage and inspect autonomous agent instances.</p>
      </div>
      
      {error && (
        <ErrorMessage message={(error as Error).message || "Failed to load orchestration data."} />
      )}

      <AgentList agents={agents} compact={false} />
    </div>
  );
}
