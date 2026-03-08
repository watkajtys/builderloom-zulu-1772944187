import { useLocation } from 'react-router-dom';

export default function Header() {
  const location = useLocation();

  const getPageTitle = (pathname: string) => {
    // Exact route mapping prevents brittle behavior when dynamic parameters are added
    const titles: Record<string, string> = {
      '/': 'Dashboard',
      '/viewer/': 'Dashboard',
      '/agents': 'Agents',
      '/viewer/agents': 'Agents',
    };
    
    // Exact matches
    if (titles[pathname]) {
      return titles[pathname];
    }
    
    // Handling trailing slashes
    if (pathname.endsWith('/') && titles[pathname.slice(0, -1)]) {
      return titles[pathname.slice(0, -1)];
    }
    
    // Fallback for unknown routes or future dynamic routes until they are added
    const baseRoute = pathname.split('/')[1];
    if (baseRoute) {
      return baseRoute.charAt(0).toUpperCase() + baseRoute.slice(1);
    }
    
    return 'Loom App';
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/30 flex items-center px-8 shrink-0 backdrop-blur-sm">
      <h2 className="text-lg font-semibold text-white capitalize">
        {getPageTitle(location.pathname)}
      </h2>
    </header>
  );
}
