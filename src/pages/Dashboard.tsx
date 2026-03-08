import { useContainers } from '../hooks/useContainers';
import { useAgents } from '../hooks/useAgents';
import { useMetrics } from '../hooks/useMetrics';
import StatCard from '../components/common/StatCard';
import ContainerList from '../components/domain/ContainerList';
import AgentList from '../components/domain/AgentList';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import { Server, Users, Activity } from 'lucide-react';

export default function Dashboard() {
  const { data: containers = [], isLoading: loadingContainers, error: errorContainers } = useContainers();
  const { data: agents = [], isLoading: loadingAgents, error: errorAgents } = useAgents();
  const { data: metrics, isLoading: loadingMetrics, error: errorMetrics } = useMetrics();

  const isLoading = loadingContainers || loadingAgents || loadingMetrics;
  const error = errorContainers || errorAgents || errorMetrics;

  if (isLoading && !metrics) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Orchestration Dashboard</h1>
          <p className="text-slate-400 text-sm">Monitoring system metrics and agent performance.</p>
        </div>
      </div>

      {error && (
        <ErrorMessage message={(error as Error).message || "Failed to load orchestration data."} />
      )}

      {/* Overview Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Active Containers"
          value={metrics?.activeContainers || 0}
          icon={<Server size={24} />}
          trend="2 today"
          trendUp={true}
        />
        <StatCard
          title="Agent Instances"
          value={metrics?.agentCount || 0}
          icon={<Users size={24} />}
        />
        <StatCard
          title="System Health"
          value={`${metrics?.systemHealth || 0}%`}
          icon={<Activity size={24} />}
          trend="Stable"
          trendUp={true}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* Docker Containers Card */}
        <ContainerList containers={containers} />

        {/* Agents Card */}
        <AgentList agents={agents} compact={true} />
      </div>
    </div>
  );
}
