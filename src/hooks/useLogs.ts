import { useEffect, useState, useRef } from 'react';

export function useLogs() {
  const [logs, setLogs] = useState<string[]>([]);
  const retryCount = useRef(0);
  const maxRetries = 10;
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let timeoutId: number;

    const connect = () => {
      // Connect to SSE endpoint
      const eventSource = new EventSource('/api/logs/stream');
      eventSourceRef.current = eventSource;
      
      eventSource.onopen = () => {
        retryCount.current = 0; // Reset on success
      };

      eventSource.onmessage = (event) => {
        try {
          const newLogs = JSON.parse(event.data);
          if (Array.isArray(newLogs) && newLogs.length > 0) {
            setLogs(prev => {
              const combined = [...prev, ...newLogs];
              // keep max 500 logs
              if (combined.length > 500) {
                return combined.slice(-500);
              }
              return combined;
            });
          }
        } catch (e) {
          console.error("Failed to parse logs", e);
        }
      };

      eventSource.onerror = (err) => {
        console.error("SSE error", err);
        eventSource.close();
        
        if (retryCount.current < maxRetries) {
          const timeout = Math.min(10000, 1000 * Math.pow(2, retryCount.current));
          retryCount.current++;
          timeoutId = window.setTimeout(connect, timeout);
        }
      };
    };

    connect();

    return () => {
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return { logs };
}
