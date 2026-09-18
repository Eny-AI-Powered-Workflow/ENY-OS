"use client";

import { useEffect, useState } from 'react';
import { MetricCard } from '@/components/MetricCard';
import { supabase } from '@/lib/supabaseClient';

export default function EnrollmentMetrics() {
  const [metrics, setMetrics] = useState({
    totalLeads: 0,
    newLeadsToday: 0,
    conversionRate: 0,
    revenuePipeline: 0,
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

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/metrics`, {
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
        totalLeads: 0,
        newLeadsToday: 0,
        conversionRate: 0,
        revenuePipeline: 0,
      });
    } catch (err: any) {
      console.error('Error fetching enrollment metrics:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const statCards = [
    { label: 'Total Leads', value: metrics.totalLeads.toLocaleString(), icon: '👥', accent: 'violet' as const },
    { label: 'New Today', value: metrics.newLeadsToday.toLocaleString(), icon: '📅', accent: 'sky' as const },
    { label: 'Conversion Rate', value: `${metrics.conversionRate}%`, icon: '📈', accent: 'emerald' as const },
    { label: 'Revenue Pipeline', value: `$${metrics.revenuePipeline.toLocaleString()}`, icon: '💰', accent: 'amber' as const },
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
