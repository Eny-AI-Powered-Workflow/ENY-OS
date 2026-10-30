"use client";

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';

const formatLiveTimestamp = (date = new Date()) =>
  new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);

export default function EnrollmentMetrics() {
  const [metrics, setMetrics] = useState({
    totalLeads: 0,
    newLeadsToday: 0,
    conversionRate: 0,
    revenuePipeline: 0,
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
      setUpdatedAt(formatLiveTimestamp());
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

  const accentClasses = {
    violet: 'border-violet-400/15 bg-violet-400/[0.07] text-violet-300',
    sky: 'border-cyan-400/15 bg-cyan-400/[0.07] text-cyan-300',
    emerald: 'border-emerald-400/15 bg-emerald-400/[0.07] text-emerald-300',
    amber: 'border-amber-400/15 bg-amber-400/[0.07] text-amber-300',
  } as const;

  const renderCards = (cardValue: (card: (typeof statCards)[number]) => string | null, helper: string) => (
    <div className="grid grid-cols-2 gap-2 sm:gap-3 xl:grid-cols-4">
      {statCards.map((card) => (
        <div key={card.label} className="relative flex min-h-[94px] min-w-0 flex-col justify-between overflow-hidden rounded-xl border border-white/[0.06] bg-[#111c2a] p-3 shadow-[0_8px_24px_rgba(2,6,23,0.18)] sm:min-h-[108px] sm:p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-400 sm:text-[10px]">{card.label}</p>
              <p className={`mt-2 truncate text-xl font-bold tracking-tight text-slate-100 sm:text-2xl ${cardValue(card) === 'Unavailable' ? 'text-rose-300' : ''}`}>{cardValue(card)}</p>
            </div>
            <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border text-sm ${accentClasses[card.accent]}`}>{card.icon}</span>
          </div>
          <div className="mt-2 flex items-center justify-between gap-2 border-t border-white/[0.05] pt-2">
            <span className="truncate text-[9px] text-slate-500">{helper}</span>
            <span className="shrink-0 rounded-full bg-[#1a2838] px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-wider text-emerald-300">{cardValue(card) === 'Unavailable' ? 'Issue' : loading ? 'Sync' : 'Live'}</span>
          </div>
        </div>
      ))}
    </div>
  );

  if (loading) {
    return renderCards(() => '—', 'Loading data');
  }

  if (error) {
    return renderCards(() => 'Unavailable', 'Retry required');
  }

  return renderCards((card) => card.value, updatedAt ? `Updated ${updatedAt}` : 'Live from enrollment services');
}
