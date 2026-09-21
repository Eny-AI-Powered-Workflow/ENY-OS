'use client';

import { useEffect, useState } from 'react';
import { MetricCard } from '@/components/MetricCard';
import { supabase } from '@/lib/supabaseClient';

export default function StudentSuccessMetrics() {
  const [metrics, setMetrics] = useState({
    totalStudents: null as number | null,
    atRiskStudents: null as number | null,
    graduationRate: null as number | null,
    interventionsToday: null as number | null,
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

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/metrics`, {
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
        totalStudents: 0,
        atRiskStudents: 0,
        graduationRate: 0,
        interventionsToday: 0,
      });
    } catch (err: any) {
      console.error('Error fetching student success metrics:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const statCards = [
    { label: 'Total Students', value: metrics.totalStudents === null ? null : metrics.totalStudents.toLocaleString(), icon: '🎓', accent: 'violet' as const },
    { label: 'At Risk Students', value: metrics.atRiskStudents === null ? null : metrics.atRiskStudents.toLocaleString(), icon: '⚠️', accent: 'rose' as const },
    { label: 'Graduation Rate', value: metrics.graduationRate === null ? null : `${metrics.graduationRate}%`, icon: '📈', accent: 'emerald' as const },
    { label: 'Interventions Today', value: metrics.interventionsToday === null ? null : metrics.interventionsToday.toLocaleString(), icon: '⚡', accent: 'sky' as const },
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
    return renderCards(() => 'Unavailable', 'Retry required');
  }

  return renderCards((card) => card.value, 'Live data');
}
