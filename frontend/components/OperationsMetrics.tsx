'use client';

import { useEffect, useState } from 'react';
import { MetricCard } from '@/components/MetricCard';
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
    { label: 'System Uptime', value: `${metrics.systemUptime}%`, icon: '⏱️', accent: 'emerald' as const },
    { label: 'Active Workflows', value: metrics.activeWorkflows.toString(), icon: '⚡', accent: 'violet' as const },
    { label: 'Tasks Completed', value: metrics.tasksCompleted.toLocaleString(), icon: '✅', accent: 'sky' as const },
    { label: 'Avg Response Time', value: `${metrics.avgResponseTime}ms`, icon: '🚀', accent: 'amber' as const },
  ];

  const renderCards = (cardValue: (card: (typeof statCards)[number]) => string, helper: string) => (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      {statCards.map((card) => (
        <MetricCard
          key={card.label}
          title={card.label}
          value={cardValue(card)}
          helper={helper}
          icon={card.icon}
          accent={card.accent}
        />
      ))}
    </div>
  );

  if (loading) {
    return renderCards(() => '—', 'Loading data');
  }

  if (error) {
    return renderCards(() => 'Unavailable', 'Retry required');
  }

  return renderCards((card) => card.value, 'Live data');
}
