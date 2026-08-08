'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { AlertTriangle, ArrowRight, ChevronDown, ChevronUp, Clock, Sparkles, Users } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

interface Lead {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string | null;
  tags: string[];
  score?: number;
}

export default function HotLeadsCard() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchLeads = async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/leads?limit=20`, {
        headers,
        credentials: 'include',
      });

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          setError('Your session has expired. Please log in again.');
        } else {
          throw new Error(`Failed to fetch leads: ${res.status}`);
        }
        return;
      }

      const data = await res.json();
      const fetchedLeads: Lead[] = data.leads || [];
      setLeads(fetchedLeads);
      if (fetchedLeads.length > 0 && !expandedId) {
        setExpandedId(fetchedLeads[0].id);
      }
    } catch (err: any) {
      console.error('Error fetching hot leads:', err);
      setError(err.message || 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
    const interval = setInterval(fetchLeads, 30_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card className="w-full overflow-hidden border border-white/10 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 text-white shadow-2xl shadow-slate-950/30">
        <CardHeader className="flex flex-col items-center py-8">
          <Clock className="mb-3 h-5 w-5 text-amber-300" />
          <CardTitle className="text-base font-medium text-slate-200">Loading hot leads...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full overflow-hidden border border-rose-500/30 bg-slate-950 text-white shadow-xl shadow-rose-950/20">
        <CardHeader className="flex flex-col items-center py-8">
          <AlertTriangle className="mb-3 h-5 w-5 text-rose-300" />
          <CardTitle className="text-base font-medium text-rose-200">{error}</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (leads.length === 0) {
    return (
      <Card className="w-full overflow-hidden border border-white/10 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 text-white shadow-2xl shadow-slate-950/30">
        <CardHeader className="flex flex-col items-center py-8">
          <Users className="mb-3 h-5 w-5 text-slate-300" />
          <CardTitle className="text-base font-medium text-slate-200">No hot leads found</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full overflow-hidden border border-white/10 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 text-white shadow-2xl shadow-slate-950/30">
      <CardHeader className="border-b border-white/10 bg-white/5 pb-5">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 text-slate-950 shadow-lg shadow-amber-500/20">
              <Users className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.24em] text-slate-400">Workflow</p>
              <h2 className="text-xl font-semibold text-white">Hot Leads</h2>
            </div>
          </div>
          <div className="rounded-full border border-amber-400/30 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-200">
            {leads.length} active
          </div>
        </div>
        <p className="mt-3 text-sm text-slate-300">
          Leads scored by the ENY-SALES-SCORE workflow and ready for follow-up.
        </p>
      </CardHeader>

      <CardContent className="space-y-3 p-4 md:p-5">
        {leads.map((lead) => {
          const isExpanded = expandedId === lead.id;
          const scoreTone = (lead.score ?? 0) >= 85 ? 'text-emerald-300' : (lead.score ?? 0) >= 70 ? 'text-amber-300' : 'text-rose-300';

          return (
            <div
              key={lead.id}
              className={`overflow-hidden rounded-2xl border transition-all duration-200 ${
                isExpanded
                  ? 'border-amber-400/40 bg-white/5 shadow-lg shadow-slate-950/20'
                  : 'border-white/10 bg-slate-950/40 hover:border-white/20'
              }`}
            >
              <button
                type="button"
                onClick={() => setExpandedId(isExpanded ? null : lead.id)}
                className="flex w-full items-start justify-between gap-4 p-4 text-left"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-base font-semibold text-white">
                      {lead.firstName} {lead.lastName}
                    </span>
                    {lead.score !== undefined && (
                      <span className={`rounded-full border border-current/20 bg-current/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${scoreTone}`}>
                        Score {lead.score}
                      </span>
                    )}
                  </div>

                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-300">
                    <span>{lead.email}</span>
                    {lead.phone && <span className="text-slate-500">•</span>}
                    {lead.phone && <span>{lead.phone}</span>}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex flex-wrap justify-end gap-1.5">
                    {lead.tags.slice(0, 2).map((tag, idx) => (
                      <span
                        key={`${lead.id}-${tag}-${idx}`}
                        className={`rounded-full px-2 py-1 text-[10px] font-medium ${
                          tag.toLowerCase().includes('hot')
                            ? 'bg-rose-500/15 text-rose-200'
                            : tag.toLowerCase().includes('follow')
                              ? 'bg-sky-500/15 text-sky-200'
                              : 'bg-slate-700/80 text-slate-200'
                        }`}
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                  {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-300" /> : <ChevronDown className="h-4 w-4 text-slate-300" />}
                </div>
              </button>

              {isExpanded && (
                <div className="border-t border-white/10 bg-slate-950/50 p-4">
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Priority</p>
                      <div className="mt-2 flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-amber-300" />
                        <span className="font-medium text-white">{(lead.score ?? 0) >= 80 ? 'High Intent' : 'Qualified'}</span>
                      </div>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Tags</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {lead.tags.map((tag, idx) => (
                          <span key={`${lead.id}-expanded-${tag}-${idx}`} className="rounded-full bg-white/5 px-2 py-1 text-[10px] text-slate-200">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Next step</p>
                      <button type="button" className="mt-2 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-2.5 py-1.5 text-[10px] font-semibold text-slate-950">
                        Contact lead
                        <ArrowRight className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}