import { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  trend?: string;
  trendUp?: boolean;
}

export default function StatCard({ title, value, icon, trend, trendUp }: StatCardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm hover:border-slate-700 transition-colors">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-1">
            {title}
          </p>
          <div className="flex items-baseline gap-2">
            <h3 className="text-3xl font-bold text-slate-100">{value}</h3>
            {trend && (
              <span className={`text-xs font-semibold ${trendUp ? 'text-emerald-400' : 'text-red-400'}`}>
                {trendUp ? '↑' : '↓'} {trend}
              </span>
            )}
          </div>
        </div>
        <div className="w-12 h-12 rounded-lg bg-slate-800/50 flex items-center justify-center text-blue-400 border border-slate-700/50">
          {icon}
        </div>
      </div>
    </div>
  );
}
