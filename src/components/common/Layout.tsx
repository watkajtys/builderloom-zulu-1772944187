import { ReactNode } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen bg-slate-950 text-slate-300 font-sans">
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        <Header />
        <div className="flex-1 overflow-auto p-8">
          <div className="max-w-6xl mx-auto">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
