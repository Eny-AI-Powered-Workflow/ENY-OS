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
      setData(payload)
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
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center gap-2"><CalendarDays className="h-4 w-4 text-cyan-600" /><h2 className="font-semibold text-slate-900">Calendar and tasks</h2></div><div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-600"><p className="font-semibold text-slate-800">{data.briefing.meetings.status}</p><p className="mt-1">{data.briefing.meetings.message}</p></div><div className="mt-3 space-y-2">{data.briefing.unresolved_tasks.map((task) => <div key={`${task.workflow}-${task.created_at}`} className="flex items-center gap-2 text-xs text-slate-600"><Clock3 className="h-3.5 w-3.5 text-amber-600" />{task.workflow} · {task.status}</div>)}</div></section>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center gap-2"><BriefcaseBusiness className="h-4 w-4 text-cyan-600" /><h2 className="font-semibold text-slate-900">Opportunities</h2></div><div className="mt-4 space-y-2">{data.briefing.opportunities.length ? data.briefing.opportunities.map((opportunity) => <div key={opportunity.id || opportunity.name} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 p-3 text-xs"><div><p className="font-semibold text-slate-800">{opportunity.name || 'Unnamed opportunity'}</p><p className="mt-1 text-slate-500">{opportunity.pipeline || 'Pipeline stage unavailable'} · {opportunity.status || 'Unknown status'}</p></div><span className="inline-flex items-center gap-1 text-amber-700"><ShieldAlert className="h-3.5 w-3.5" /> Approval required</span></div>) : <p className="text-sm text-slate-500">No live opportunities available.</p>}</div></section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" /><h2 className="font-semibold text-slate-900">EA playbooks</h2></div><div className="mt-4 space-y-2">{data.playbooks.map((playbook) => <div key={playbook.name} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 p-3 text-xs"><span className="font-medium text-slate-800">{playbook.name}</span><span className={playbook.status === 'active' ? 'text-emerald-700' : 'text-slate-500'}>{playbook.status}{playbook.requires_approval ? ' · approval required' : ''}</span></div>)}</div><div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">{data.approval_boundary.message}</div></section>
      </div>
    </div>
  )
}
