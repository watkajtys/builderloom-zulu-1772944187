import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
export default function Layout({ children }: { children: ReactNode }) { return <div className="min-h-screen bg-slate-950 text-white"><header className="p-4 border-b border-slate-800"><Link to="/">Loom Zulu</Link></header><main>{children}</main></div>; }