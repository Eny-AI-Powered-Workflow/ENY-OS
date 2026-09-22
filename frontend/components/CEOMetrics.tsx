'use client';

import { useEffect, useState } from 'react';
import { MetricCard } from '@/components/MetricCard';
import { supabase } from '@/lib/supabaseClient';

const formatLiveTimestamp = (date = new Date()) =>
  new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);

export default function CEOMetrics() {
  const [metrics, setMetrics] = useState({
    activeUsers: 0,
    aiAgents: 0,
    tasksCompleted: 0,
    systemUptime: null as number | null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string>('');

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ceo/metrics`, {
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
        activeUsers: 0,
        aiAgents: 0,
        tasksCompleted: 0,
        systemUptime: 0,
      });
      setUpdatedAt(formatLiveTimestamp());
    } catch (err: any) {
      console.error('Error fetching CEO metrics:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const statCards = [
    { label: 'Active Users', value: metrics.activeUsers.toLocaleString(), icon: '👥', accent: 'violet' as const },
    { label: 'AI Agents', value: metrics.aiAgents.toString(), icon: '🤖', accent: 'sky' as const },
    { label: 'Tasks Completed', value: metrics.tasksCompleted.toLocaleString(), icon: '✅', accent: 'emerald' as const },
    { label: 'System Uptime', value: metrics.systemUptime === null ? null : `${metrics.systemUptime}%`, icon: '⏱️', accent: 'amber' as const },
  ];

  const renderCards = (cardValue: (card: (typeof statCards)[number]) => string | null, helper: string) => (
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
    return renderCards((card) => card.label === 'System Uptime' ? 'Unavailable' : '—', 'Retry required');
  }

  return renderCards((card) => card.value, updatedAt ? `Updated ${updatedAt}` : 'Live from CEO services');
}
