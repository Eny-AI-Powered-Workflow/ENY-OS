// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/enrollment-operations/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, Clock3, RefreshCw, UserRound } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'

type Operation = {
  id: string
  contact_id: string
  contact_name: string | null
  email: string | null
  source: string | null
  score: number | null
  queue_status: string
  follow_up_status: string
  assigned_user_id: string | null
  error: string | null
  retry_count: number
  created_at: string | null
}

type OperationsPayload = {
  summary: Record<string, number>
  results: Operation[]
  audit_events: Array<{ id: string; event_type: string; result_id: string | null; created_at: string | null }>
}

const statusStyles: Record<string, string> = {
  new: 'bg-slate-100 text-slate-700',
  assigned: 'bg-amber-100 text-amber-800',
  contacted: 'bg-cyan-100 text-cyan-800',
  qualified: 'bg-emerald-100 text-emerald-800',
  closed: 'bg-slate-200 text-slate-600',
}

export default function EnrollmentOperationsPage() {
  const [data, setData] = useState<OperationsPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/operations?limit=100`, {
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        credentials: 'include',
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load Enrollment operations')
      setData(payload)
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load Enrollment operations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    const timer = setInterval(load, 30_000)
    return () => clearInterval(timer)
  }, [])

  const summary = data?.summary || {}

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-col gap-4 rounded-[28px] border border-cyan-300/20 bg-[radial-gradient(circle_at_top_right,_rgba(34,211,238,0.16),_transparent_35%),linear-gradient(135deg,_rgba(8,47,73,0.95),_rgba(15,23,42,0.98))] p-6 sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div><p className="text-[10px] uppercase tracking-[0.24em] text-cyan-200">Enrollment control room</p><h1 className="mt-2 text-3xl font-black text-white">Follow-up operations</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">Track every approved hot lead from assignment through CRM follow-up and closure.</p></div>
          <button type="button" onClick={() => void load()} title="Refresh operations" className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"><RefreshCw className="h-4 w-4" /></button>
        </div>
      </header>

      {error && <div className="rounded-xl border border-rose-300/30 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

      <section className="grid grid-cols-2 gap-3 md:grid-cols-6">
        {['total', 'new', 'assigned', 'contacted', 'qualified', 'closed'].map((key) => <div key={key} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-[10px] uppercase tracking-[0.16em] text-slate-400">{key.replace('_', ' ')}</p><p className="mt-2 text-2xl font-bold text-slate-900">{loading ? '...' : summary[key] || 0}</p></div>)}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Shared queue</p><h2 className="text-lg font-semibold text-slate-900">Lead follow-up status</h2></div><Activity className="h-5 w-5 text-cyan-600" /></div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">Lead</th><th className="px-5 py-3">Source</th><th className="px-5 py-3">Score</th><th className="px-5 py-3">Queue</th><th className="px-5 py-3">Follow-up</th><th className="px-5 py-3">Owner</th><th className="px-5 py-3">Result</th></tr></thead><tbody className="divide-y divide-slate-100">{data?.results.map((row) => <tr key={row.id} className="hover:bg-slate-50"><td className="px-5 py-4"><p className="font-medium text-slate-900">{row.contact_name || row.contact_id}</p><p className="text-xs text-slate-500">{row.email || row.contact_id}</p></td><td className="px-5 py-4 text-slate-600">{row.source || 'Unknown'}</td><td className="px-5 py-4 font-semibold text-slate-900">{row.score ?? '—'}</td><td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusStyles[row.queue_status] || statusStyles.new}`}>{row.queue_status}</span></td><td className="px-5 py-4"><span className="inline-flex items-center gap-1 text-xs text-slate-600">{row.follow_up_status === 'tagged' ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> : <Clock3 className="h-3.5 w-3.5 text-amber-600" />}{row.follow_up_status}</span></td><td className="px-5 py-4 text-xs text-slate-500">{row.assigned_user_id ? <span className="inline-flex items-center gap-1"><UserRound className="h-3.5 w-3.5" /> Assigned</span> : 'Unassigned'}</td><td className="px-5 py-4 text-xs">{row.error ? <span className="inline-flex items-center gap-1 text-rose-600"><AlertTriangle className="h-3.5 w-3.5" />{row.error}</span> : <span className="text-slate-500">{row.execution_status}</span>}</td></tr>)}</tbody></table>
          {(!data?.results.length && !loading) && <div className="p-8 text-center text-sm text-slate-500">No approved follow-up operations recorded yet.</div>}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-2"><Activity className="h-4 w-4 text-cyan-600" /><h2 className="font-semibold text-slate-900">Recent audit activity</h2></div><div className="mt-4 grid gap-2 md:grid-cols-2">{data?.audit_events.slice(0, 12).map((event) => <div key={event.id} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-xs"><span className="font-medium text-slate-700">{event.event_type.replaceAll('_', ' ')}</span><span className="text-slate-400">{event.created_at ? new Date(event.created_at).toLocaleString() : '—'}</span></div>)}</div></section>
    </div>
  )
}
