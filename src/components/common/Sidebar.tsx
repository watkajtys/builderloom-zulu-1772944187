import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, Settings } from 'lucide-react';

export default function Sidebar() {
  const location = useLocation();

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Agents', path: '/agents', icon: Users },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/50 flex flex-col">
      <div className="p-6 border-b border-slate-800 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center shadow-[0_0_15px_rgba(59,130,246,0.5)]">
          <Settings size={18} className="text-white animate-[spin_4s_linear_infinite]" />
        </div>
        <div>
          <h1 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">BuilderLoom</h1>
          <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">Zulu Edition</p>
        </div>
      </div>
      
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive 
                  ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' 
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent'
              }`}
            >
              <Icon size={18} className={isActive ? 'text-blue-400' : 'text-slate-500'} />
              {item.name}
            </Link>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          SYSTEM ONLINE
        </div>
      </div>
    </aside>
  );
}
