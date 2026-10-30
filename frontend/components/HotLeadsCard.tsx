'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { AlertTriangle, ArrowRight, Check, ChevronDown, ChevronUp, Clock, Flame, Mail, Phone, Search, Sparkles, Users } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

interface Lead {
  id: string;
  result_id?: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string | null;
  tags: string[];
  assigned_user_id?: string | null;
  last_comment?: string | null;
  follow_up_status?: string;
  follow_up_retry_approved?: boolean;
  score?: number;
  score_origin?: string;
  score_reasoning?: string | null;
  score_factors?: Record<string, number> | null;
  score_evidence?: string[] | null;
  score_unknowns?: string[] | null;
  next_best_action?: string | null;
  status?: string;
  assigned_to_current_user?: boolean;
  lifecycle_stage?: string;
  next_step?: string | null;
}

interface TeamMember {
  id: string;
  name: string;
  email: string | null;
}

function formatActionError(detail: unknown, action: string): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') {
    const value = detail as { message?: string; error?: string; contact_id?: string };
    return [value.message || `Unable to ${action} lead`, value.error, value.contact_id ? `Contact: ${value.contact_id}` : '']
      .filter(Boolean)
      .join(' · ');
  }
  return `Unable to ${action} lead`;
}

function formatResponseError(status: number, detail: unknown, action: string): string {
  if (status === 403 && typeof detail === 'string' && detail.includes('Permission denied')) {
    return 'Your role does not have permission to contact leads. Ask an administrator to grant leads:write.';
  }
  if (status === 403 && typeof detail === 'string' && detail.includes('Claim the lead')) {
    return 'Claim this lead first, then contact it from your assigned queue.';
  }
  return formatActionError(detail, action);
}

export default function HotLeadsCard() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [leadTab, setLeadTab] = useState<'all' | 'assigned' | 'mine' | 'unassigned'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actingId, setActingId] = useState<string | null>(null);

  const actOnLead = async (lead: Lead, action: 'claim' | 'follow-up') => {
    if (!lead.result_id) return;
    setActingId(lead.result_id);
    setActionMessage(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/hot-leads/${lead.result_id}/${action}`, {
        method: 'POST',
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(formatResponseError(res.status, data.detail, action));
      const successMessage = action === 'claim' ? 'Lead assigned to you.' : (data.message || 'Sales & Enrollment notified; the lead was not contacted.');
      setActionMessage(data.warning ? `${successMessage} ${data.warning}` : successMessage);
      await fetchLeads();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Lead action failed');
    } finally {
      setActingId(null);
    }
  };

  const updateLifecycle = async (lead: Lead, stage: 'outreach_sent' | 'responded' | 'next_step' | 'booked' | 'enrolled' | 'lost') => {
    if (!lead.result_id) return;
    const reason = window.prompt(stage === 'enrolled'
      ? 'Verify payment and Programs onboarding in their source systems, then enter the confirmation references/details:'
      : `Reason for ${stage.replace('_', ' ')}:`);
    if (!reason?.trim()) return;
    setActingId(lead.result_id);
    setActionMessage(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/hot-leads/${lead.result_id}/lifecycle`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
        },
        credentials: 'include',
        body: JSON.stringify({ stage, reason: reason.trim(), next_step: stage === 'next_step' ? reason.trim() : undefined, enrollment_outcome: stage === 'enrolled' || stage === 'lost' ? stage : undefined }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(formatActionError(data.detail, `update lifecycle to ${stage}`));
      const message = stage === 'enrolled'
        ? 'Enrollment outcome recorded in ENY. Payment was not verified and Programs onboarding was not triggered by this action.'
        : `Lifecycle updated to ${stage.replace('_', ' ')}.`;
      setActionMessage(data.warning ? `${message} ${data.warning}` : message);
      await fetchLeads();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Lifecycle update failed');
    } finally {
      setActingId(null);
    }
  };

  const fetchLeads = async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/hot-leads?limit=20&min_score=85`, {
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

  const fetchTeamMembers = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/team-members`, {
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        credentials: 'include',
      });
      if (!res.ok) throw new Error(`Unable to load team assignments: ${res.status}`);
      const data = await res.json();
      setTeamMembers(data.members || []);
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Unable to load team assignments');
    }
  };

  useEffect(() => {
    fetchLeads();
    fetchTeamMembers();
    const interval = setInterval(() => {
      void fetchLeads();
      void fetchTeamMembers();
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  const visibleLeads = leads.filter((lead) => {
    const matchesTab = leadTab === 'assigned'
      ? Boolean(lead.assigned_user_id)
      : leadTab === 'mine'
        ? lead.assigned_to_current_user === true
        : leadTab === 'unassigned'
          ? !lead.assigned_user_id
          : true;
    const query = searchTerm.trim().toLowerCase();
    const matchesSearch = !query || [
      lead.firstName,
      lead.lastName,
      lead.email,
      lead.phone || '',
      lead.assigned_user_id || '',
      lead.tags.join(' '),
      lead.lifecycle_stage || '',
    ].some((value) => value.toLowerCase().includes(query));
    return matchesTab && matchesSearch;
  });

  if (loading) {
    return (
      <Card className="w-full overflow-hidden border border-white/[0.06] bg-[#111722] text-white shadow-xl shadow-black/20">
        <CardHeader className="flex flex-col items-center py-12">
          <Clock className="mb-3 h-5 w-5 animate-pulse text-amber-300" />
          <CardTitle className="text-base font-medium text-slate-200">Loading hot leads...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full overflow-hidden border border-rose-500/30 bg-[#111722] text-white shadow-xl shadow-rose-950/20">
        <CardHeader className="flex flex-col items-center py-8">
          <AlertTriangle className="mb-3 h-5 w-5 text-rose-300" />
          <CardTitle className="text-base font-medium text-rose-200">{error}</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (leads.length === 0) {
    return (
      <Card className="w-full overflow-hidden border border-white/[0.06] bg-[#111722] text-white shadow-xl shadow-black/20">
        <CardHeader className="flex flex-col items-center py-8">
          <Users className="mb-3 h-5 w-5 text-amber-300" />
          <CardTitle className="text-base font-medium text-slate-200">No hot leads found</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full overflow-hidden rounded-2xl border border-white/[0.06] bg-[#111722] text-white shadow-xl shadow-black/20">
      <CardHeader className="border-b border-white/[0.06] bg-[#111722] pb-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-amber-300 to-amber-500 text-[#17120a] shadow-lg shadow-amber-500/15">
              <Flame className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-slate-400">ENY Pipeline</p>
              <h2 className="text-lg font-semibold text-slate-100">Sales Accelerator</h2>
            </div>
          </div>
          <div className="rounded-full border border-amber-400/20 bg-amber-500/[0.08] px-3 py-1.5 text-xs font-medium text-amber-300">
            {visibleLeads.length} {visibleLeads.length === 1 ? 'lead' : 'leads'}
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            ['All leads', leads.length, 'text-amber-300'],
            ['Assigned', leads.filter((lead) => Boolean(lead.assigned_user_id)).length, 'text-cyan-300'],
            ['My leads', leads.filter((lead) => lead.assigned_to_current_user === true).length, 'text-emerald-300'],
            ['First touch', leads.filter((lead) => lead.status === 'contacted').length, 'text-violet-300'],
          ].map(([label, count, tone]) => (
            <div key={label} className="rounded-xl bg-[#0b1019] px-3 py-2.5">
              <p className="text-[10px] text-slate-400">{label}</p>
              <p className={`mt-0.5 text-base font-semibold ${tone}`}>{count}</p>
            </div>
          ))}
        </div>
        {actionMessage && <p role="status" className="mt-3 rounded-lg border border-amber-400/20 bg-amber-400/[0.06] px-3 py-2.5 text-xs leading-5 text-amber-100">{actionMessage}</p>}
      </CardHeader>

      <CardContent className="space-y-4 p-3 sm:p-4 lg:p-5">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Filter hot leads">
          {([
            ['all', 'All leads', leads.length],
            ['assigned', 'Assigned', leads.filter((lead) => Boolean(lead.assigned_user_id)).length],
            ['mine', 'My leads', leads.filter((lead) => lead.assigned_to_current_user === true).length],
            ['unassigned', 'Unassigned', leads.filter((lead) => !lead.assigned_user_id).length],
          ] as const).map(([tab, label, count]) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={leadTab === tab}
              onClick={() => setLeadTab(tab)}
              className={`flex min-h-10 shrink-0 items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold transition ${leadTab === tab ? 'bg-amber-400 text-[#17120a] shadow-md shadow-amber-500/10' : 'bg-[#1a2230] text-slate-400 hover:bg-[#222c3c] hover:text-slate-100'}`}
            >
              {label}<span className={leadTab === tab ? 'text-slate-800/70' : 'text-slate-500'}>{count}</span>
            </button>
          ))}
          </div>
          <label className="flex h-10 w-full items-center gap-2.5 rounded-xl border border-white/[0.05] bg-[#0b1019] px-3 text-slate-500 xl:max-w-sm">
            <Search className="h-4 w-4 shrink-0" />
            <input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Search name, email, phone, tags..." aria-label="Search hot leads" className="min-w-0 flex-1 bg-transparent text-xs text-slate-100 outline-none placeholder:text-slate-500" />
          </label>
        </div>
        {!visibleLeads.length && <p className="rounded-xl border border-white/[0.06] bg-[#0b1019] p-8 text-center text-sm text-slate-400">No leads match this view.</p>}
        <div className="grid grid-cols-1 items-start gap-3 xl:grid-cols-2 2xl:grid-cols-3">
        {visibleLeads.map((lead) => {
          const isExpanded = expandedId === lead.id;
          const scoreTone = (lead.score ?? 0) >= 85 ? 'text-emerald-300' : (lead.score ?? 0) >= 70 ? 'text-amber-300' : 'text-rose-300';
          const assignedMember = teamMembers.find((member) => member.id === lead.assigned_user_id);

          return (
            <div
              key={lead.id}
              className={`overflow-hidden rounded-2xl border transition-all duration-200 ${
                isExpanded
                  ? 'border-amber-400/40 bg-[#171e2b] shadow-lg shadow-amber-950/10'
                  : 'border-white/[0.06] bg-[#151c28] hover:border-white/[0.12]'
              }`}
            >
              <button
                type="button"
                onClick={() => setExpandedId(isExpanded ? null : lead.id)}
                aria-expanded={isExpanded}
                className="flex min-h-[92px] w-full items-start justify-between gap-3 p-3.5 text-left transition hover:bg-white/[0.015] sm:p-4"
              >
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-xs font-bold ${isExpanded ? 'bg-amber-400 text-[#17120a]' : 'bg-[#263142] text-slate-300'}`}>
                    {`${lead.firstName.charAt(0)}${lead.lastName.charAt(0)}`.toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="truncate text-sm font-semibold text-slate-100 sm:text-[15px]">
                      {lead.firstName} {lead.lastName}
                    </span>
                    {lead.score !== undefined && (
                      <span className={`rounded-md border border-current/20 bg-current/[0.05] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${scoreTone}`}>
                        Score {lead.score}
                      </span>
                    )}
                  </div>

                  <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                    <span className="truncate">{lead.email}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className="rounded-md bg-[#263142] px-2 py-1 text-[9px] font-medium text-slate-300">
                      {assignedMember ? `Assigned: ${assignedMember.name}` : lead.assigned_user_id ? `Assigned: ${lead.assigned_user_id.slice(0, 8)}` : 'Unassigned'}
                    </span>
                    <span className="rounded-md border border-cyan-400/20 bg-cyan-400/[0.07] px-2 py-1 text-[9px] font-medium capitalize text-cyan-200">
                      {lead.status || 'new'}
                    </span>
                    <span className="rounded-md border border-rose-400/15 bg-rose-400/[0.06] px-2 py-1 text-[9px] font-medium capitalize text-rose-200">
                      {(lead.lifecycle_stage || 'not_started').replaceAll('_', ' ')}
                    </span>
                    {lead.last_comment && (
                      <span className="max-w-full truncate rounded-md bg-[#263142] px-2 py-1 text-[9px] text-slate-300" title={lead.last_comment}>
                        Comment: {lead.last_comment}
                      </span>
                    )}
                  </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex flex-wrap justify-end gap-1.5">
                    {lead.tags.slice(0, 2).map((tag, idx) => (
                      <span
                        key={`${lead.id}-${tag}-${idx}`}
                        className={`rounded-md px-2 py-1 text-[9px] font-medium ${
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
                  {isExpanded ? <ChevronUp className="h-4 w-4 shrink-0 text-amber-300" /> : <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />}
                </div>
              </button>

              {isExpanded && (
                <div className="border-t border-amber-400/10 bg-[#0e141e] p-3.5 sm:p-4">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">Lead details & next action</span>
                    <div className="flex items-center gap-2">
                      {lead.phone && <a href={`tel:${lead.phone.replace(/[^\d+]/g, '')}`} onClick={(event) => event.stopPropagation()} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-emerald-400/20 bg-emerald-400/[0.08] px-3 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-400/[0.14]"><Phone className="h-3.5 w-3.5" />Call</a>}
                      {lead.email && <a href={`mailto:${lead.email}`} onClick={(event) => event.stopPropagation()} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-cyan-400/20 bg-cyan-400/[0.08] px-3 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-400/[0.14]"><Mail className="h-3.5 w-3.5" />Email</a>}
                    </div>
                  </div>
                  <div className="grid gap-2.5 md:grid-cols-2">
                    <div className="rounded-xl border border-white/[0.06] bg-[#171e2b] p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Priority</p>
                      <div className="mt-2 flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-amber-300" />
                        <span className="font-medium text-white">{(lead.score ?? 0) >= 85 ? 'Hot lead' : 'Qualified'}</span>
                      </div>
                    </div>
                    <div className="rounded-xl border border-white/[0.06] bg-[#171e2b] p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Tags</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {lead.tags.map((tag, idx) => (
                          <span key={`${lead.id}-expanded-${tag}-${idx}`} className="rounded-md bg-[#263142] px-2 py-1 text-[10px] text-slate-200">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-xl border border-white/[0.06] bg-[#171e2b] p-3 md:col-span-2">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Next step</p>
                      <p className="mt-2 text-xs font-medium text-cyan-200">{lead.next_best_action || lead.lifecycle_stage?.replaceAll('_', ' ') || 'not started'}</p>
                      {lead.next_step && <p className="mt-1 text-xs text-slate-400">{lead.next_step}</p>}
                      {lead.score_reasoning && <p className="mt-2 text-xs leading-5 text-slate-300">{lead.score_reasoning}</p>}
                      {lead.score_factors && <p className="mt-2 text-[10px] text-slate-400">AI score · intent {lead.score_factors.intent_score ?? 0} · fit {lead.score_factors.fit_score ?? 0} · engagement {lead.score_factors.engagement_score ?? 0} ({lead.score_origin || 'unknown'})</p>}
                      {lead.score_evidence?.length ? <p className="mt-1 text-[10px] text-slate-400">Evidence: {lead.score_evidence.join('; ')}</p> : null}
                      {lead.score_unknowns?.length ? <p className="mt-1 text-[10px] text-amber-200">Unknown: {lead.score_unknowns.join('; ')}</p> : null}
                      <div className="mt-2 flex flex-wrap gap-2">
                        {lead.status !== 'assigned' && lead.status !== 'contacted' && (
                          <button type="button" onClick={() => actOnLead(lead, 'claim')} disabled={actingId === lead.result_id} className="inline-flex items-center gap-2 rounded-full border border-amber-300/30 px-2.5 py-1.5 text-[10px] font-semibold text-amber-200 disabled:opacity-60">
                            <Check className="h-3 w-3" /> Claim
                          </button>
                        )}
                        {lead.assigned_to_current_user && lead.status === 'assigned' && !['triggering', 'tagged', 'team_notified'].includes(lead.follow_up_status || '') && (lead.follow_up_status !== 'failed' || lead.follow_up_retry_approved) ? (
                          <button type="button" onClick={() => actOnLead(lead, 'follow-up')} disabled={actingId === lead.result_id} className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-2.5 py-1.5 text-[10px] font-semibold text-slate-950 disabled:opacity-60">
                            {lead.follow_up_status === 'failed' ? 'Retry team notification' : 'Notify Sales & Enrollment'}
                            <ArrowRight className="h-3 w-3" />
                          </button>
                        ) : lead.assigned_to_current_user && lead.status === 'assigned' && lead.follow_up_status === 'failed' ? (
                          <span className="text-[10px] font-medium text-rose-200">Review the GHL tag alert before retrying</span>
                        ) : lead.assigned_to_current_user && lead.status === 'assigned' && lead.follow_up_status === 'triggering' ? (
                          <span className="text-[10px] font-medium text-amber-200">Follow-up is in progress</span>
                        ) : lead.assigned_to_current_user && lead.status === 'assigned' && lead.follow_up_status === 'tagged' ? (
                          <span className="text-[10px] font-medium text-emerald-200">Team notified; lead not contacted</span>
                        ) : lead.assigned_to_current_user && lead.status === 'assigned' && lead.follow_up_status === 'team_notified' ? (
                          <span className="text-[10px] font-medium text-emerald-200">Team notified; human outreach pending</span>
                        ) : lead.assigned_to_current_user && lead.status === 'contacted' ? (
                          <span className="text-[10px] font-medium text-emerald-200">First contact complete</span>
                        ) : lead.status === 'assigned' ? (
                          <span className="text-[10px] font-medium text-slate-400">Assigned to another user</span>
                        ) : null}
                        {lead.assigned_to_current_user && lead.lifecycle_stage === 'queued' && <button type="button" onClick={() => void updateLifecycle(lead, 'outreach_sent')} disabled={actingId === lead.result_id} className="min-h-9 rounded-lg border border-sky-300/30 bg-sky-300/[0.06] px-3 text-[10px] font-semibold text-sky-200 transition hover:bg-sky-300/[0.12] disabled:opacity-60">Mark outreach sent</button>}
                        {lead.assigned_to_current_user && ['queued', 'outreach_sent'].includes(lead.lifecycle_stage || '') && <button type="button" onClick={() => void updateLifecycle(lead, 'responded')} disabled={actingId === lead.result_id} className="min-h-9 rounded-lg bg-gradient-to-r from-amber-300 to-amber-500 px-3 text-[10px] font-semibold text-[#17120a] transition hover:brightness-105 disabled:opacity-60"><Check className="mr-1 inline h-3 w-3" />Mark responded</button>}
                        {lead.assigned_to_current_user && lead.lifecycle_stage === 'responded' && <button type="button" onClick={() => void updateLifecycle(lead, 'next_step')} disabled={actingId === lead.result_id} className="min-h-9 rounded-lg border border-cyan-300/30 bg-cyan-300/[0.06] px-3 text-[10px] font-semibold text-cyan-200 transition hover:bg-cyan-300/[0.12] disabled:opacity-60">Set next step</button>}
                        {lead.assigned_to_current_user && ['responded', 'next_step'].includes(lead.lifecycle_stage || '') && <button type="button" onClick={() => void updateLifecycle(lead, 'booked')} disabled={actingId === lead.result_id} className="min-h-9 rounded-lg border border-violet-300/30 bg-violet-300/[0.06] px-3 text-[10px] font-semibold text-violet-200 transition hover:bg-violet-300/[0.12] disabled:opacity-60">Mark booked</button>}
                        {lead.assigned_to_current_user && lead.lifecycle_stage === 'booked' && <button type="button" onClick={() => void updateLifecycle(lead, 'enrolled')} disabled={actingId === lead.result_id} className="min-h-9 rounded-lg border border-amber-300/30 bg-amber-300/[0.06] px-3 text-[10px] font-semibold text-amber-200 transition hover:bg-amber-300/[0.12] disabled:opacity-60">Record enrolled (manual)</button>}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
        </div>
      </CardContent>
    </Card>
  );
}