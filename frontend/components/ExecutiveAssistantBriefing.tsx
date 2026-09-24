'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, BriefcaseBusiness, CalendarDays, CheckCircle2, Clock3, RefreshCw, ShieldAlert, Sparkles } from 'lucide-react'
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
  coordination?: { calendar?: { status?: string; items?: unknown[] }; tasks?: { status?: string; items?: unknown[] }; conflicts?: unknown[] }
  research?: Array<{ id: string; title: string; source_url: string; confidence: string; status: string; summary: string }>
  actions?: Array<{ id: string; title: string; action_type: string; status: string; priority: string; due_at: string | null }>
  action_history?: Array<{ id: string; event_type: string; details: Record<string, unknown>; created_at: string | null }>
  reporting?: { tasks_completed_on_time?: { percent?: number }; research_quality?: { approved?: number; total?: number }; escalations?: { open?: number }; workflow_failures?: number; sop_adherence?: { percent?: number } }
}

export default function ExecutiveAssistantBriefing() {
  const [data, setData] = useState<Briefing | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  if (loading && !data) return <div className="rounded-[24px] border border-slate-800 bg-slate-950 p-8 text-sm text-slate-400">Preparing the executive briefing...</div>
  if (error && !data) return <div className="rounded-[24px] border border-rose-500/30 bg-rose-950/30 p-6 text-sm text-rose-200">{error}</div>
  if (!data) return null

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
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-[24px] border border-slate-800 bg-[radial-gradient(circle_at_top_right,_rgba(56,189,248,0.16),_transparent_34%),linear-gradient(135deg,_rgba(15,23,42,0.98),_rgba(14,116,144,0.12))] p-6 text-white shadow-[0_24px_60px_rgba(15,23,42,0.3)]">
        <div><p className="text-[10px] uppercase tracking-[0.24em] text-cyan-300">Executive Assistant</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Daily briefing</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">Priorities, alerts, opportunities, and unresolved work gathered from connected systems.</p></div>
        <button type="button" onClick={() => void load()} title="Refresh briefing" className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/5 text-slate-200 hover:bg-white/10"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4"><p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Open priorities</p><p className="mt-2 text-2xl font-bold text-slate-900">{data.briefing.priorities.length}</p><p className="mt-1 text-xs text-slate-500">Source-labelled and confidence-rated</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4"><p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">CRM status</p><p className={`mt-2 text-2xl font-bold ${data.system_status.crm === 'connected' ? 'text-emerald-700' : 'text-amber-700'}`}>{data.system_status.crm}</p><p className="mt-1 text-xs text-slate-500">{data.system_status.sop_chunks} EA SOP knowledge chunks</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4"><p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Open alerts</p><p className="mt-2 text-2xl font-bold text-rose-700">{data.system_status.open_alerts}</p><p className="mt-1 text-xs text-slate-500">Requires operational review</p></div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-cyan-600" /><h2 className="font-semibold text-slate-900">Priority queue</h2></div><div className="mt-4 space-y-3">{data.briefing.priorities.length ? data.briefing.priorities.map((item, index) => <div key={`${item.title}-${index}`} className="rounded-xl border border-slate-100 bg-slate-50 p-3"><div className="flex items-start gap-3"><AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${item.severity === 'critical' ? 'text-rose-600' : 'text-amber-600'}`} /><div className="min-w-0"><p className="text-sm font-semibold text-slate-900">{item.title}</p><p className="mt-1 text-xs text-slate-500">{item.reason}</p><p className="mt-2 text-[10px] uppercase tracking-wide text-slate-400">{item.source} · {item.confidence} confidence · {item.source_timestamp ? new Date(item.source_timestamp).toLocaleString() : 'No timestamp'}</p></div></div></div>) : <p className="text-sm text-slate-500">No active priorities.</p>}</div></section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center gap-2"><CalendarDays className="h-4 w-4 text-cyan-600" /><h2 className="font-semibold text-slate-900">Calendar and tasks</h2></div><div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-600"><p className="font-semibold text-slate-800">Calendar: {data.coordination?.calendar?.status || data.briefing.meetings.status}</p><p className="mt-1">{data.briefing.meetings.message}</p><p className="mt-2 font-semibold text-slate-800">Tasks: {data.coordination?.tasks?.status || 'internal activity'}</p><p className="mt-1">{data.coordination?.conflicts?.length || 0} scheduling conflicts detected.</p></div><div className="mt-3 space-y-2">{data.briefing.unresolved_tasks.map((task) => <div key={`${task.workflow}-${task.created_at}`} className="flex items-center gap-2 text-xs text-slate-600"><Clock3 className="h-3.5 w-3.5 text-amber-600" />{task.workflow} · {task.status}</div>)}</div></section>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center gap-2"><BriefcaseBusiness className="h-4 w-4 text-cyan-600" /><h2 className="font-semibold text-slate-900">Opportunities</h2></div><div className="mt-4 space-y-2">{data.briefing.opportunities.length ? data.briefing.opportunities.map((opportunity) => <div key={opportunity.id || opportunity.name} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 p-3 text-xs"><div><p className="font-semibold text-slate-800">{opportunity.name || 'Unnamed opportunity'}</p><p className="mt-1 text-slate-500">{opportunity.pipeline || 'Pipeline stage unavailable'} · {opportunity.status || 'Unknown status'}</p></div><span className="inline-flex items-center gap-1 text-amber-700"><ShieldAlert className="h-3.5 w-3.5" /> Approval required</span></div>) : <p className="text-sm text-slate-500">No live opportunities available.</p>}</div></section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" /><h2 className="font-semibold text-slate-900">EA playbooks</h2></div><div className="mt-4 space-y-2">{data.playbooks.map((playbook) => <div key={playbook.name} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 p-3 text-xs"><span className="font-medium text-slate-800">{playbook.name}</span><span className={playbook.status === 'active' ? 'text-emerald-700' : 'text-slate-500'}>{playbook.status}{playbook.requires_approval ? ' · approval required' : ''}</span></div>)}</div><div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">{data.approval_boundary.message}</div></section>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-amber-600" /><h2 className="font-semibold text-slate-900">Research briefs awaiting review</h2></div><div className="mt-4 space-y-2">{data.research?.length ? data.research.map((brief) => <div key={brief.id} className="rounded-xl bg-slate-50 p-3"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-semibold text-slate-800">{brief.title}</p><span className="text-xs font-medium text-amber-700">{brief.status} · {brief.confidence}</span></div><p className="mt-1 text-xs text-slate-500">{brief.summary}</p><a className="mt-2 block truncate text-xs text-cyan-700 hover:underline" href={brief.source_url} target="_blank" rel="noreferrer">{brief.source_url}</a></div>) : <p className="text-sm text-slate-500">No research briefs have been submitted.</p>}</div></section>

      <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center justify-between gap-3"><div><p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Action ledger</p><h2 className="mt-1 font-semibold text-slate-900">EA actions</h2></div><span className="text-xs text-slate-500">Status is audited</span></div><div className="mt-4 space-y-2">{data.actions?.length ? data.actions.slice(0, 8).map((action) => <div key={action.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 p-3 text-xs"><div><p className="font-semibold text-slate-800">{action.title}</p><p className="mt-1 text-slate-500">{action.action_type} · {action.priority} · {action.status}{action.due_at ? ` · due ${new Date(action.due_at).toLocaleString()}` : ''}</p></div><div className="flex gap-2">{action.status === 'open' && <button type="button" onClick={() => void updateAction(action.id, 'in_progress')} className="rounded-lg border border-cyan-200 px-2 py-1 font-semibold text-cyan-700">Start</button>}{action.status !== 'completed' && <button type="button" onClick={() => void updateAction(action.id, 'completed')} className="rounded-lg border border-emerald-200 px-2 py-1 font-semibold text-emerald-700">Complete</button>}</div></div>) : <p className="text-sm text-slate-500">No EA actions have been created.</p>}</div></section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Reporting and audit</p><div className="mt-3 grid grid-cols-2 gap-3 text-xs"><div><span className="text-slate-500">On-time tasks</span><strong className="float-right text-slate-900">{data.reporting?.tasks_completed_on_time?.percent ?? 0}%</strong></div><div><span className="text-slate-500">Research approved</span><strong className="float-right text-slate-900">{data.reporting?.research_quality?.approved ?? 0}/{data.reporting?.research_quality?.total ?? 0}</strong></div><div><span className="text-slate-500">Escalations</span><strong className="float-right text-rose-700">{data.reporting?.escalations?.open ?? 0}</strong></div><div><span className="text-slate-500">SOP adherence</span><strong className="float-right text-emerald-700">{data.reporting?.sop_adherence?.percent ?? 0}%</strong></div></div><div className="mt-4 border-t border-slate-100 pt-3"><p className="text-xs font-semibold text-slate-700">Recent action history</p>{data.action_history?.slice(0, 3).map((event) => <p key={event.id} className="mt-2 text-[11px] text-slate-500">{event.event_type} · {event.created_at ? new Date(event.created_at).toLocaleString() : 'unknown time'}</p>)}</div></section>
      </div>
    </div>
  )
}
