'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';

export default function OperationsMetrics() {
  const [metrics, setMetrics] = useState({
    systemUptime: 0,
    activeWorkflows: 0,
    tasksCompleted: 0,
    avgResponseTime: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/operations/metrics`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch metrics: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      setMetrics(data.metrics || {
        systemUptime: 0,
        activeWorkflows: 0,
        tasksCompleted: 0,
        avgResponseTime: 0,
      });
    } catch (err: any) {
      console.error('Error fetching operations metrics:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const statCards = [
    { label: 'System Uptime', value: `${metrics.systemUptime}%`, icon: '⏱️' },
    { label: 'Active Workflows', value: metrics.activeWorkflows.toString(), icon: '⚡' },
    { label: 'Tasks Completed', value: metrics.tasksCompleted.toLocaleString(), icon: '✅' },
    { label: 'Avg Response Time', value: `${metrics.avgResponseTime}ms`, icon: '🚀' },
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((card) => (
          <div key={card.label} className="bg-card/50 backdrop-blur-sm rounded-xl p-6 border border-border/50">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">{card.label}</p>
                <p className="text-2xl font-bold text-muted-foreground">Loading...</p>
              </div>
              <div className="w-12 h-12 bg-brass-500/10 rounded-full flex items-center justify-center">
                <span className="text-brass-500 text-xl">{card.icon}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((card) => (
          <div key={card.label} className="bg-card/50 backdrop-blur-sm rounded-xl p-6 border border-border/50">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">{card.label}</p>
                <p className="text-2xl font-bold text-destructive">Error loading</p>
              </div>
              <div className="w-12 h-12 bg-brass-500/10 rounded-full flex items-center justify-center">
                <span className="text-brass-500 text-xl">{card.icon}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {statCards.map((card) => (
        <div key={card.label} className="bg-card/50 backdrop-blur-sm rounded-xl p-6 border border-border/50">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">{card.label}</p>
              <p className="text-2xl font-bold text-foreground">{card.value}</p>
            </div>
            <div className="w-12 h-12 bg-brass-500/10 rounded-full flex items-center justify-center">
              <span className="text-brass-500 text-xl">{card.icon}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
