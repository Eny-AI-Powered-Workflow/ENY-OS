'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { AlertTriangle, ArrowRight, Check, ChevronDown, ChevronUp, Clock, Sparkles, Users } from 'lucide-react';
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
    if (leadTab === 'assigned') return Boolean(lead.assigned_user_id);
    if (leadTab === 'mine') return lead.assigned_to_current_user === true;
    if (leadTab === 'unassigned') return !lead.assigned_user_id;
    return true;
  });

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
            {visibleLeads.length} leads
          </div>
        </div>
        <p className="mt-3 text-sm text-slate-300">
          Leads scored by the ENY-SALES-SCORE workflow and ready for follow-up.
        </p>
        {actionMessage && <p className="mt-2 text-xs text-amber-200">{actionMessage}</p>}
      </CardHeader>

      <CardContent className="space-y-3 p-4 md:p-5">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter hot leads">
          {([
            ['all', 'All leads'],
            ['assigned', 'Assigned'],
            ['mine', 'My leads'],
            ['unassigned', 'Unassigned'],
          ] as const).map(([tab, label]) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={leadTab === tab}
              onClick={() => setLeadTab(tab)}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold ${leadTab === tab ? 'bg-amber-400 text-slate-950' : 'border border-white/10 text-slate-300 hover:bg-white/5'}`}
            >
              {label}
            </button>
          ))}
        </div>
        {!visibleLeads.length && <p className="rounded-xl border border-white/10 bg-slate-950/40 p-5 text-center text-sm text-slate-400">No leads match this view.</p>}
        {visibleLeads.map((lead) => {
          const isExpanded = expandedId === lead.id;
          const scoreTone = (lead.score ?? 0) >= 85 ? 'text-emerald-300' : (lead.score ?? 0) >= 70 ? 'text-amber-300' : 'text-rose-300';
          const assignedMember = teamMembers.find((member) => member.id === lead.assigned_user_id);

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
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className="rounded-full bg-violet-500/15 px-2 py-1 text-[10px] font-medium text-violet-200">
                      {assignedMember ? `Assigned: ${assignedMember.name}` : lead.assigned_user_id ? `Assigned: ${lead.assigned_user_id.slice(0, 8)}` : 'Unassigned'}
                    </span>
                    <span className="rounded-full bg-cyan-500/15 px-2 py-1 text-[10px] font-medium capitalize text-cyan-200">
                      {lead.status || 'new'}
                    </span>
                    <span className="rounded-full bg-emerald-500/15 px-2 py-1 text-[10px] font-medium capitalize text-emerald-200">
                      {(lead.lifecycle_stage || 'not_started').replaceAll('_', ' ')}
                    </span>
                    {lead.last_comment && (
                      <span className="max-w-full truncate rounded-full bg-slate-700/80 px-2 py-1 text-[10px] text-slate-200" title={lead.last_comment}>
                        Comment: {lead.last_comment}
                      </span>
                    )}
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
                        <span className="font-medium text-white">{(lead.score ?? 0) >= 85 ? 'Hot lead' : 'Qualified'}</span>
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
                        {lead.assigned_to_current_user && lead.lifecycle_stage === 'queued' && <button type="button" onClick={() => void updateLifecycle(lead, 'outreach_sent')} disabled={actingId === lead.result_id} className="rounded-full border border-sky-300/30 px-2.5 py-1.5 text-[10px] font-semibold text-sky-200 disabled:opacity-60">Mark outreach sent</button>}
                        {lead.assigned_to_current_user && ['queued', 'outreach_sent'].includes(lead.lifecycle_stage || '') && <button type="button" onClick={() => void updateLifecycle(lead, 'responded')} disabled={actingId === lead.result_id} className="rounded-full border border-emerald-300/30 px-2.5 py-1.5 text-[10px] font-semibold text-emerald-200 disabled:opacity-60">Mark responded</button>}
                        {lead.assigned_to_current_user && lead.lifecycle_stage === 'responded' && <button type="button" onClick={() => void updateLifecycle(lead, 'next_step')} disabled={actingId === lead.result_id} className="rounded-full border border-cyan-300/30 px-2.5 py-1.5 text-[10px] font-semibold text-cyan-200 disabled:opacity-60">Set next step</button>}
                        {lead.assigned_to_current_user && ['responded', 'next_step'].includes(lead.lifecycle_stage || '') && <button type="button" onClick={() => void updateLifecycle(lead, 'booked')} disabled={actingId === lead.result_id} className="rounded-full border border-violet-300/30 px-2.5 py-1.5 text-[10px] font-semibold text-violet-200 disabled:opacity-60">Mark booked</button>}
                        {lead.assigned_to_current_user && lead.lifecycle_stage === 'booked' && <button type="button" onClick={() => void updateLifecycle(lead, 'enrolled')} disabled={actingId === lead.result_id} className="rounded-full border border-amber-300/30 px-2.5 py-1.5 text-[10px] font-semibold text-amber-200 disabled:opacity-60">Record enrolled (manual)</button>}
                      </div>
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