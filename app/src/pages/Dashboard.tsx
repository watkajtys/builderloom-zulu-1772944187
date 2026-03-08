import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Header from '../components/dashboard/Header';
import Sidebar from '../components/dashboard/Sidebar';
import LogViewer from '../components/dashboard/LogViewer';
import Topology from '../components/dashboard/Topology';
import { useTelemetry } from '../hooks/useTelemetry';

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filterParam = searchParams.get('filter') || 'all'; // e.g. 'error', 'all', 'warnings'
  
  const [showInfo, setShowInfo] = useState(true);
  const [showWarnings, setShowWarnings] = useState(true);
  const [showErrors, setShowErrors] = useState(true);

  // Parse existing URL search params if present to maintain backward compatibility for the tests
  useEffect(() => {
    if (filterParam === 'error') {
      setShowInfo(false);
      setShowWarnings(false);
      setShowErrors(true);
    }
  }, [filterParam]);

  const { data: telemetryData, error: telemetryError } = useTelemetry();
  
  const logs = telemetryData?.logs || [];
  const version = telemetryData?.version || '';
  const error = telemetryError?.message || null;

  const handleErrorToggle = () => {
    // If turning on error only, turn others off. Otherwise just toggle.
    // For the specific test "toggles the 'Errors Only' filter", if we click this, 
    // it expects only errors to show.
    if (!showErrors || (showInfo || showWarnings)) {
        setShowInfo(false);
        setShowWarnings(false);
        setShowErrors(true);
        setSearchParams(new URLSearchParams({ filter: 'error' }));
    } else {
        setShowInfo(true);
        setShowWarnings(true);
        setShowErrors(true);
        setSearchParams(new URLSearchParams());
    }
  };

  const filteredLogs = logs.filter(log => {
    const isError = log.level === 'error';
    const isWarning = log.level === 'warning';
    const isInfo = log.level === 'info' || log.level === 'thought';
    
    if (isError && !showErrors) return false;
    if (isWarning && !showWarnings) return false;
    if (isInfo && !showInfo) return false;
    
    return true;
  });

  return (
    <div className="bg-background-dark text-slate-100 overflow-hidden h-screen flex flex-col selection:bg-neon-green selection:text-black">
      <Header />
      
      <main className="flex flex-1 overflow-hidden p-2 gap-2 bg-black grid-bg">
        <Sidebar 
          showInfo={showInfo} 
          setShowInfo={setShowInfo} 
          showWarnings={showWarnings} 
          setShowWarnings={setShowWarnings} 
          showErrors={showErrors} 
          handleErrorToggle={handleErrorToggle} 
        />
        <LogViewer logs={filteredLogs} error={error} />
        <Topology />
      </main>
      
      <footer className="bg-primary text-white h-6 flex items-center justify-between px-4 text-[10px] font-bold uppercase tracking-widest border-t-2 border-white/20">
        <div className="flex gap-4">
          <span className="flex items-center gap-1 font-mono"><span className="w-2 h-2 bg-white animate-pulse"></span> ZULU_CORE: STABLE</span>
          <span className="font-mono">KERNEL: BL_v9.2.0</span>
          <span className="font-mono">LOC: SUBTERRANEAN_NODE_4</span>
        </div>
        <div className="flex gap-4 font-mono">
          <span className="hidden md:inline">FABRIC_UPTIME: 91,004:12:04</span>
          <span className="hidden md:inline">CRYPT: ZULU_E2EE</span>
          <span className="bg-white text-primary px-2" id="clock">14:22:15 UTC</span>
        </div>
      </footer>
    </div>
  );
}
