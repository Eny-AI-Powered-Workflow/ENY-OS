'use client';

import { useEffect, useState } from 'react';
import { MetricCard } from '@/components/MetricCard';
import { supabase } from '@/lib/supabaseClient';

const formatLiveTimestamp = (date = new Date()) =>
  new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);

export default function MarketingMetrics() {
  const [metrics, setMetrics] = useState({
    totalLeads: null as number | null,
    leadsThisMonth: null as number | null,
    conversionRate: null as number | null,
    roi: null as number | null,
    status: 'not_configured',
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

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/metrics`, {
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
        totalLeads: null,
        leadsThisMonth: null,
        conversionRate: null,
        roi: null,
        status: 'not_configured',
      });
      setUpdatedAt(formatLiveTimestamp());
    } catch (err: any) {
      console.error('Error fetching marketing metrics:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const statCards = [
    { label: 'Total Leads', value: metrics.totalLeads?.toLocaleString() ?? null, icon: '📢', accent: 'violet' as const },
    { label: 'Leads This Month', value: metrics.leadsThisMonth?.toLocaleString() ?? null, icon: '📅', accent: 'sky' as const },
    { label: 'Conversion Rate', value: metrics.conversionRate === null ? null : `${metrics.conversionRate}%`, icon: '📈', accent: 'emerald' as const },
    { label: 'ROI', value: metrics.roi === null ? null : `${metrics.roi.toFixed(1)}x`, icon: '💰', accent: 'amber' as const },
  ];

  const renderCards = (cardValue: (card: (typeof statCards)[number]) => string | null, helper: string) => (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
    return (
      <div className="space-y-6">
        <h2 className="text-lg font-semibold text-foreground">Key Performance Indicators</h2>
        {renderCards(() => '—', 'Loading data')}
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h2 className="text-lg font-semibold text-foreground">Key Performance Indicators</h2>
        {renderCards(() => 'Unavailable', 'Retry required')}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-foreground">Key Performance Indicators</h2>
      {renderCards((card) => card.value, metrics.status === 'connected' && updatedAt ? `GHL · updated ${updatedAt}` : 'GoHighLevel not configured')}
    </div>
  );
}
