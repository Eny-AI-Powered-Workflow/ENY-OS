'use client';

import { useEffect, useState } from 'react';
import { MetricCard } from '@/components/MetricCard';
import { supabase } from '@/lib/supabaseClient';

const formatLiveTimestamp = (date = new Date()) =>
  new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);

export default function StudentSuccessMetrics({ offerId }: { offerId: string }) {
  const [metrics, setMetrics] = useState({
    totalStudents: null as number | null,
    activeOffer: null as string | null,
  });
  const [programSheetStatus, setProgramSheetStatus] = useState<string | null>(null);
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

      const params = new URLSearchParams({ offer_id: offerId });
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/metrics?${params}`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        if (res.status === 401) throw new Error('Your session has expired. Please log in again.');
        if (res.status === 403) throw new Error('You do not have permission to view student metrics.');
        if (res.status === 503 && payload?.detail?.code === 'provider_not_configured') {
          throw new Error('Kajabi is not configured in the backend environment.');
        }
        throw new Error(`Failed to fetch metrics: ${res.status}`);
      }

      const data = await res.json();
      setMetrics(data.metrics || { totalStudents: null, activeOffer: null });
      setProgramSheetStatus(data.sources?.program_sheet ?? null);
      setUpdatedAt(formatLiveTimestamp());
    } catch (err: any) {
      console.error('Error fetching student success metrics:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchMetrics();
  }, [offerId]);

  const statCards = [
    { label: 'Active Kajabi learners', value: metrics.totalStudents?.toLocaleString() ?? null, icon: '🎓', accent: 'violet' as const },
    { label: 'Selected offer', value: metrics.activeOffer, icon: '▤', accent: 'sky' as const },
    { label: 'Program Sheet', value: programSheetStatus?.replaceAll('_', ' ') ?? null, icon: '▦', accent: 'emerald' as const },
  ];

  const renderCards = (cardValue: (card: (typeof statCards)[number]) => string | null, helper: string) => (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
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
    return renderCards(() => 'Unavailable', error);
  }

  return renderCards((card) => card.value, updatedAt ? `Updated ${updatedAt}` : 'Live from student success services');
}
