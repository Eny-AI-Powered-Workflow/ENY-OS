'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, BriefcaseBusiness, CalendarDays, CheckCircle2, Clock3, RefreshCw, ShieldAlert, Sparkles, Zap } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'

type Briefing = {
  briefing: {
    priorities: Array<{ title: string; reason: string; severity: string; source: string; source_timestamp: string | null; confidence: string }>
    meetings: { status: string; message: string; confidence: string }
    unresolved_tasks: Array<{ workflow: string; status: string; created_at: string | null }>
    alerts: Array<{ id: string; severity: string; source: string; message: string; created_at: string | null }>
    opportunities: Array<{ id?: string; name?: string; pipeline?: string; status?: string; value?: number; requires_approval?: boolean }>
  }
  system_status: { crm: string; open_alerts: number; sop_chunks: number }
  approval_boundary: { message: string; requires_ceo_approval: boolean }
  playbooks: Array<{ name: string; status: string; requires_approval: boolean }>
  coordination?: { calendar?: { status?: string; error?: string; items?: unknown[] }; tasks?: { status?: string; error?: string; items?: unknown[] }; conflicts?: unknown[] }
  research?: Array<{ id: string; title: string; source_url: string; confidence: string; status: string; summary: string }>
  actions?: Array<{ id: string; title: string; action_type: string; status: string; priority: string; due_at: string | null }>
  action_history?: Array<{ id: string; event_type: string; details: Record<string, unknown>; created_at: string | null }>
  reporting?: { tasks_completed_on_time?: { percent?: number }; research_quality?: { approved?: number; total?: number }; escalations?: { open?: number }; workflow_failures?: number; sop_adherence?: { percent?: number } }
}

type ExecutiveAssistantBriefingProps = {
  headingLevel?: 'h1' | 'h2'
}

export default function ExecutiveAssistantBriefing({ headingLevel = 'h1' }: ExecutiveAssistantBriefingProps) {
  const [data, setData] = useState<Briefing | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const calendarStatusMessage = () => {
    const calendar = data?.coordination?.calendar
    if (calendar?.status === 'connected') {
      return `${calendar.items?.length || 0} upcoming Google Calendar events loaded.`
    }
    switch (calendar?.error) {
      case 'calendar_google_api_auth_failed':
        return 'Google Calendar rejected the token. Check that the Calendar API is enabled and re-authorize with the calendar.events.readonly scope.'
      case 'google_oauth_refresh_failed':
        return 'Google OAuth could not refresh its access token. Check the Render OAuth client credentials and refresh token.'
      case 'google_oauth_configuration_incomplete':
        return 'Google OAuth credentials are incomplete in the backend environment.'
      case 'google_api_rate_limited':
        return 'Google Calendar rate limit reached; try refreshing shortly.'
      case 'provider_unavailable':
        return 'Google Calendar is temporarily unavailable.'
      case 'google_api_request_failed':
        return 'Google Calendar rejected the request. Check the API configuration and retry.'
      case 'provider_invalid_response':
        return 'Google Calendar returned an invalid response.'
      default:
        return data?.briefing.meetings.message || 'Calendar integration is not connected.'
    }
  }

  const load = async () => {
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/executive-assistant/briefing`, {
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        credentials: 'include',
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load executive briefing')
      const [coordinationResponse, researchResponse, actionsResponse, reportingResponse] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/executive-assistant/coordination`, { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/executive-assistant/research`, { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/executive-assistant/actions`, { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/executive-assistant/reporting`, { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' }),
      ])
      const coordination = coordinationResponse.ok ? await coordinationResponse.json() : null
      const research = researchResponse.ok ? (await researchResponse.json()).briefs || [] : []
      const actions = actionsResponse.ok ? (await actionsResponse.json()).actions || [] : []
      const reporting = reportingResponse.ok ? await reportingResponse.json() : null
      let action_history = []
      if (actions[0]) {
        const historyResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/executive-assistant/actions/${actions[0].id}/history`, { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' })
        action_history = historyResponse.ok ? (await historyResponse.json()).events || [] : []
      }
      setData({ ...payload, coordination, research, actions, action_history, reporting })
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load executive briefing')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    const timer = setInterval(() => void load(), 60_000)
    return () => clearInterval(timer)
  }, [])

  if (loading && !data) return <div role="status" className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-sm text-slate-300">Preparing the executive briefing...</div>
  if (error && !data) return <div role="alert" className="rounded-2xl border border-rose-500/30 bg-rose-950/30 p-6 text-sm text-rose-200">{error}</div>
  if (!data) return null

  const Heading = headingLevel
  const approvalCount = data.briefing.opportunities.filter((opportunity) => opportunity.requires_approval !== false).length
  const updateAction = async (actionId: string, status: 'in_progress' | 'completed') => {
    const { data: { session } } = await supabase.auth.getSession()
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/executive-assistant/actions/${actionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}) },
      credentials: 'include',
      body: JSON.stringify({ status, note: `Updated from Executive Assistant workspace to ${status}.` }),
    })
    await load()
  }

  return (
    <div className="space-y-5 sm:space-y-6">
      <section className="relative overflow-hidden rounded-2xl border border-slate-800 bg-[radial-gradient(circle_at_top_right,_rgba(6,182,212,0.12),_transparent_38%),linear-gradient(115deg,_#0b1120_0%,_#111a30_55%,_#0c1d2b_100%)] p-5 shadow-xl sm:p-7">
        <div className="pointer-events-none absolute -bottom-24 left-1/3 h-56 w-56 rounded-full bg-indigo-500/[0.08] blur-3xl" />
        <div className="relative flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div className="space-y-1.5">
            <p className="inline-flex items-center gap-2 text-[10px] font-mono font-bold uppercase tracking-[0.18em] text-cyan-300">
              Executive Assistant <span className="h-1 w-1 rounded-full bg-cyan-400" />
              <span className="font-sans font-normal normal-case tracking-normal text-slate-400">Connected systems briefing</span>
            </p>
            <Heading className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">Daily briefing</Heading>
            <p className="max-w-2xl text-sm leading-6 text-slate-300">Priorities, alerts, opportunities, and unresolved work gathered from connected systems.</p>
          </div>
          <button type="button" onClick={() => void load()} title="Refresh briefing" aria-label="Refresh briefing" disabled={loading} className="flex h-10 w-10 shrink-0 items-center justify-center self-start rounded-xl border border-slate-700 bg-slate-800/80 text-slate-200 shadow-sm transition hover:border-slate-600 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 sm:self-center">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </section>

      {error && <p role="alert" className="rounded-xl border border-rose-900/60 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">{error}</p>}

      <section aria-label="Executive briefing metrics" className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-700/70 bg-slate-900/70 p-4 transition hover:border-amber-500/40 sm:p-5">
          <div className="flex items-center justify-between"><span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Open priorities</span><span className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-1.5 text-amber-300"><Zap className="h-4 w-4" /></span></div>
          <p className="mt-3 text-3xl font-extrabold tracking-tight text-white">{data.briefing.priorities.length}<span className="ml-2 inline-block h-1.5 w-1.5 rounded-full bg-amber-400 align-middle" /></p>
          <p className="mt-1 text-xs text-slate-400">Source-labelled and confidence-rated</p>
        </article>
        <article className="rounded-2xl border border-slate-700/70 bg-slate-900/70 p-4 transition hover:border-emerald-500/40 sm:p-5">
          <div className="flex items-center justify-between"><span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">CRM status</span><span className={`rounded-lg border p-1.5 ${data.system_status.crm === 'connected' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300' : 'border-amber-500/20 bg-amber-500/10 text-amber-300'}`}><CheckCircle2 className="h-4 w-4" /></span></div>
          <p className={`mt-3 text-2xl font-bold tracking-tight ${data.system_status.crm === 'connected' ? 'text-emerald-300' : 'text-amber-300'}`}>{data.system_status.crm}</p>
          <p className="mt-1 text-xs text-slate-400">{data.system_status.sop_chunks} EA SOP knowledge chunks</p>
        </article>
        <article className="rounded-2xl border border-slate-700/70 bg-slate-900/70 p-4 transition hover:border-rose-500/40 sm:p-5">
          <div className="flex items-center justify-between"><span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Open alerts</span><span className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-1.5 text-rose-300"><AlertTriangle className="h-4 w-4" /></span></div>
          <p className="mt-3 text-3xl font-extrabold tracking-tight text-rose-300">{data.system_status.open_alerts}<span className="ml-2 inline-block h-1.5 w-1.5 rounded-full bg-rose-400 align-middle" /></p>
          <p className="mt-1 text-xs text-slate-400">Requires operational review</p>
        </article>
        <article className="rounded-2xl border border-slate-700/70 bg-slate-900/70 p-4 transition hover:border-indigo-500/40 sm:p-5">
          <div className="flex items-center justify-between"><span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">CEO approvals</span><span className="rounded-lg border border-indigo-500/20 bg-indigo-500/10 p-1.5 text-indigo-300"><BriefcaseBusiness className="h-4 w-4" /></span></div>
          <p className="mt-3 text-3xl font-extrabold tracking-tight text-white">{approvalCount}<span className="ml-2 inline-block h-1.5 w-1.5 rounded-full bg-indigo-400 align-middle" /></p>
          <p className="mt-1 text-xs text-slate-400">Opportunities awaiting sign-off</p>
        </article>
      </section>

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-12">
        <div className="min-w-0 space-y-5 xl:col-span-7">
          <section className="rounded-2xl border border-slate-800 bg-slate-900/65 p-4 shadow-xl sm:p-5" aria-labelledby="ea-priorities-heading">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2.5"><span className="rounded-lg border border-teal-500/20 bg-teal-500/10 p-1.5 text-teal-300"><Sparkles className="h-5 w-5" /></span><h2 id="ea-priorities-heading" className="text-base font-bold tracking-tight text-white">Priority queue</h2></div>
              <span className="rounded-md border border-slate-700 bg-slate-800/80 px-2.5 py-1 font-mono text-[10px] text-slate-300">Ranked by priority</span>
            </div>
            <div className="mt-4 space-y-3">
              {data.briefing.priorities.length ? data.briefing.priorities.map((item, index) => (
                <article key={`${item.title}-${index}`} className={`rounded-xl border p-3 transition sm:p-4 ${item.severity === 'critical' ? 'border-rose-900/50 bg-rose-950/15 hover:bg-rose-950/25' : 'border-slate-700/70 bg-slate-800/45 hover:bg-slate-800/70'}`}>
                  <div className="flex items-start gap-3">
                    <span className={`mt-0.5 shrink-0 rounded-lg border p-1 ${item.severity === 'critical' ? 'border-rose-500/20 bg-rose-500/10 text-rose-300' : 'border-amber-500/20 bg-amber-500/10 text-amber-300'}`}><AlertTriangle className="h-4 w-4" /></span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-100">{item.title}</p>
                      <p className="mt-1 text-xs leading-5 text-slate-400">{item.reason}</p>
                      <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] font-mono uppercase tracking-wide text-slate-400">
                        <span className="font-semibold text-slate-300">{item.source}</span><span className="text-slate-600">·</span>
                        <span className={item.severity === 'critical' ? 'text-rose-300' : 'text-amber-300'}>{item.confidence} confidence</span><span className="text-slate-600">·</span>
                        <span>{item.source_timestamp ? new Date(item.source_timestamp).toLocaleString() : 'No timestamp'}</span>
                      </p>
                    </div>
                  </div>
                </article>
              )) : <p className="rounded-xl border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">No active priorities.</p>}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-900/65 p-4 shadow-xl sm:p-5" aria-labelledby="ea-opportunities-heading">
            <div className="flex items-center justify-between gap-3 border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2.5"><span className="rounded-lg border border-cyan-500/20 bg-cyan-500/10 p-1.5 text-cyan-300"><BriefcaseBusiness className="h-5 w-5" /></span><h2 id="ea-opportunities-heading" className="text-base font-bold tracking-tight text-white">Opportunities</h2></div>
              <span className="rounded-md border border-slate-700 bg-slate-800/80 px-2.5 py-1 font-mono text-[10px] text-slate-300">{approvalCount} pending approval</span>
            </div>
            <div className="mt-3 divide-y divide-slate-800/80">
              {data.briefing.opportunities.length ? data.briefing.opportunities.map((opportunity) => (
                <div key={opportunity.id || opportunity.name} className="flex flex-wrap items-center justify-between gap-3 rounded-lg px-2 py-3 transition hover:bg-slate-800/40">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-100">{opportunity.name || 'Unnamed opportunity'}{opportunity.pipeline && <span className="font-normal text-slate-400"> — {opportunity.pipeline}</span>}</p>
                    <p className="mt-1 text-xs text-slate-400">{opportunity.status || 'Unknown status'}{typeof opportunity.value === 'number' ? ` · ${opportunity.value.toLocaleString()}` : ''}</p>
                  </div>
                  {opportunity.requires_approval !== false && <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-1 text-[10px] font-semibold text-amber-300"><ShieldAlert className="h-3.5 w-3.5" /> Approval required</span>}
                </div>
              )) : <p className="py-5 text-sm text-slate-400">No live opportunities available.</p>}
            </div>
          </section>
        </div>

        <div className="min-w-0 space-y-5 xl:col-span-5">
          <section className="rounded-2xl border border-slate-800 bg-slate-900/65 p-4 shadow-xl sm:p-5" aria-labelledby="ea-calendar-heading">
            <div className="flex items-center gap-2.5 border-b border-slate-800 pb-4"><span className="rounded-lg border border-sky-500/20 bg-sky-500/10 p-1.5 text-sky-300"><CalendarDays className="h-5 w-5" /></span><h2 id="ea-calendar-heading" className="text-base font-bold tracking-tight text-white">Calendar and tasks</h2></div>
            <div className="mt-3 rounded-xl border border-slate-700/70 bg-slate-800/40 p-3 text-xs">
              <p className="font-semibold text-slate-200">Calendar: <span className="rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">{data.coordination?.calendar?.status || data.briefing.meetings.status}</span></p>
              <p className="mt-2 leading-5 text-slate-400">{calendarStatusMessage()}</p>
              <div className="my-3 border-t border-slate-700/70" />
              <p className="font-semibold text-slate-200">Tasks: <span className="rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">{data.coordination?.tasks?.status || 'internal activity'}</span></p>
              {data.coordination?.tasks?.error && <p className="mt-2 break-words text-slate-400">Google Tasks: {data.coordination.tasks.error}</p>}
              <p className="mt-2 text-slate-400">{data.coordination?.conflicts?.length || 0} scheduling conflicts detected.</p>
            </div>
            {data.briefing.unresolved_tasks.length > 0 && <div className="mt-3 space-y-2">
              <h3 className="text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-400">Unresolved work</h3>
              {data.briefing.unresolved_tasks.map((task) => <div key={`${task.workflow}-${task.created_at}`} className="flex items-start gap-2 rounded-lg border border-slate-800 bg-slate-800/35 p-2.5 text-xs text-slate-300"><Clock3 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" /><span className="min-w-0 break-words">{task.workflow} · {task.status}</span></div>)}
            </div>}
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-900/65 p-4 shadow-xl sm:p-5" aria-labelledby="ea-playbooks-heading">
            <div className="flex items-center gap-2.5 border-b border-slate-800 pb-4"><span className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-1.5 text-emerald-300"><CheckCircle2 className="h-5 w-5" /></span><h2 id="ea-playbooks-heading" className="text-base font-bold tracking-tight text-white">EA playbooks</h2></div>
            <div className="mt-3 space-y-2">
              {data.playbooks.map((playbook) => <div key={playbook.name} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-700/70 bg-slate-800/40 p-3"><span className="text-sm font-medium text-slate-200">{playbook.name}</span><span className={`text-right text-[10px] font-mono ${playbook.status === 'active' ? 'rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-emerald-300' : 'text-slate-400'}`}>{playbook.status}{playbook.requires_approval ? ' · approval required' : ''}</span></div>)}
              {!data.playbooks.length && <p className="text-sm text-slate-400">No playbooks are available.</p>}
            </div>
            <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-amber-500/20 bg-amber-500/[0.08] p-3 text-xs leading-5 text-amber-200"><ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" /><p>{data.approval_boundary.message}</p></div>
          </section>
        </div>
      </div>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/65 p-4 shadow-xl sm:p-5" aria-labelledby="ea-research-heading">
        <div className="flex items-center gap-2.5 border-b border-slate-800 pb-4"><span className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-1.5 text-amber-300"><ShieldAlert className="h-4 w-4" /></span><h2 id="ea-research-heading" className="text-sm font-bold tracking-tight text-white">Research briefs awaiting review</h2><span className="ml-auto rounded-md border border-slate-700 bg-slate-800/80 px-2 py-1 font-mono text-[10px] text-slate-300">{data.research?.length || 0} briefs</span></div>
        <div className="mt-3 space-y-2">
          {data.research?.length ? data.research.map((brief) => <article key={brief.id} className="rounded-xl border border-slate-700/70 bg-slate-800/35 p-3"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-semibold text-slate-100">{brief.title}</p><span className="text-xs font-medium text-amber-300">{brief.status} · {brief.confidence}</span></div><p className="mt-1 text-xs leading-5 text-slate-400">{brief.summary}</p><a className="mt-2 block truncate text-xs text-cyan-300 hover:text-cyan-200 hover:underline" href={brief.source_url} target="_blank" rel="noreferrer">{brief.source_url}</a></article>) : <p className="text-xs text-slate-400">No research briefs have been submitted.</p>}
        </div>
      </section>

      <div className="grid grid-cols-1 items-stretch gap-5 lg:grid-cols-12">
        <section className="flex min-w-0 flex-col rounded-2xl border border-slate-800 bg-slate-900/65 p-4 shadow-xl sm:p-5 lg:col-span-7" aria-labelledby="ea-actions-heading">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div><p className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Action ledger</p><h2 id="ea-actions-heading" className="mt-1 font-semibold text-white">EA actions</h2></div>
            <span className="rounded-full border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-[10px] font-mono text-slate-300">Status is audited</span>
          </div>
          <div className="mt-3 flex-1 space-y-2">
            {data.actions?.length ? data.actions.slice(0, 8).map((action) => <article key={action.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-700/70 bg-slate-800/35 p-3 text-xs"><div className="min-w-0"><p className="font-semibold text-slate-100">{action.title}</p><p className="mt-1 text-slate-400">{action.action_type} · {action.priority} · {action.status}{action.due_at ? ` · due ${new Date(action.due_at).toLocaleString()}` : ''}</p></div><div className="flex shrink-0 gap-2">{action.status === 'open' && <button type="button" onClick={() => void updateAction(action.id, 'in_progress')} className="rounded-lg border border-cyan-500/25 px-2.5 py-1.5 font-semibold text-cyan-300 transition hover:bg-cyan-500/10">Start</button>}{action.status !== 'completed' && <button type="button" onClick={() => void updateAction(action.id, 'completed')} className="rounded-lg border border-emerald-500/25 px-2.5 py-1.5 font-semibold text-emerald-300 transition hover:bg-emerald-500/10">Complete</button>}</div></article>) : <p className="py-2 text-sm text-slate-400">No EA actions have been created.</p>}
          </div>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-4 text-[10px] font-mono text-slate-400"><span>Action status is recorded in the audit trail.</span><span>Executive Assistant workspace</span></div>
        </section>

        <section className="flex min-w-0 flex-col rounded-2xl border border-slate-800 bg-slate-900/65 p-4 shadow-xl sm:p-5 lg:col-span-5" aria-labelledby="ea-reporting-heading">
          <div className="border-b border-slate-800 pb-4"><p id="ea-reporting-heading" className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Reporting and audit</p></div>
          <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-800/30 p-2.5 text-xs"><span className="text-slate-400">On-time tasks</span><strong className="font-mono text-white">{data.reporting?.tasks_completed_on_time?.percent ?? 0}%</strong></div>
            <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-800/30 p-2.5 text-xs"><span className="text-slate-400">Research approved</span><strong className="font-mono text-white">{data.reporting?.research_quality?.approved ?? 0}/{data.reporting?.research_quality?.total ?? 0}</strong></div>
            <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-800/30 p-2.5 text-xs"><span className="text-slate-400">Escalations</span><strong className="font-mono text-rose-300">{data.reporting?.escalations?.open ?? 0}</strong></div>
            <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-800/30 p-2.5 text-xs"><span className="text-slate-400">SOP adherence</span><strong className="font-mono text-emerald-300">{data.reporting?.sop_adherence?.percent ?? 0}%</strong></div>
          </div>
          <div className="mt-5 flex-1 border-t border-slate-800 pt-4">
            <p className="text-xs font-semibold text-indigo-300">Recent action history</p>
            {data.action_history?.length ? data.action_history.slice(0, 3).map((event) => <p key={event.id} className="mt-2 text-[11px] text-slate-400">{event.event_type.replaceAll('_', ' ')} · {event.created_at ? new Date(event.created_at).toLocaleString() : 'unknown time'}</p>) : <p className="mt-2 text-xs text-slate-500">No recent action history.</p>}
          </div>
        </section>
      </div>
    </div>
  )
}
