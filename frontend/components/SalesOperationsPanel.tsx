'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Clock3, ExternalLink, Filter, RefreshCw, UserRound } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'

type Operation = {
  id: string
  contact_id: string
  contact_name: string | null
  email: string | null
  source: string | null
  score: number | null
  score_origin: string
  queue_status: string
  assigned_user_id: string | null
  follow_up_status: string
  notification_status: string
  notification_error: string | null
  last_action_at: string | null
  retry_available: boolean
  next_action: string
  ghl_contact_reference: string
  error: string | null
  execution_status: string
}

type Payload = {
  summary: Record<string, number>
  results: Operation[]
}

const statuses = ['all', 'new', 'assigned', 'contacted', 'qualified', 'closed']

export default function SalesOperationsPanel() {
  const [data, setData] = useState<Payload>({ summary: {}, results: [] })
  const [status, setStatus] = useState('all')
  const [scope, setScope] = useState('all')
  const [source, setSource] = useState('all')
  const [score, setScore] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const params = new URLSearchParams({ limit: '200' })
      if (status !== 'all') params.set('status', status)
      if (scope === 'mine') params.set('mine', 'true')
      if (scope === 'unassigned') params.set('unassigned', 'true')
      if (source !== 'all') params.set('source', source)
      if (score === 'hot') params.set('min_score', '85')
      if (score === 'qualified') params.set('min_score', '70')

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/operations?${params.toString()}`, {
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        credentials: 'include',
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load Sales operations')
      setData(payload)
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load Sales operations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    const timer = setInterval(load, 30_000)
    return () => clearInterval(timer)
  }, [status, scope, source, score])

  const sources = Array.from(new Set(data.results.map((row) => row.source).filter(Boolean))) as string[]
  const summary = data.summary
  const cards = [
    ['New hot leads', summary.new_hot || 0, 'text-amber-700'],
    ['My assigned leads', summary.my_assigned || 0, 'text-cyan-700'],
    ['Uncontacted assigned', summary.uncontacted_assigned || 0, 'text-orange-700'],
    ['Contacted today', summary.contacted_today || 0, 'text-emerald-700'],
    ['Workflow failures', summary.workflow_failures || 0, 'text-rose-700'],
    ['Avg response time', summary.average_response_minutes ? `${summary.average_response_minutes}m` : '—', 'text-slate-700'],
  ]

  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Sales control surface</p>
          <h2 className="mt-1 text-xl font-semibold text-slate-900">Lead operations</h2>
          <p className="mt-1 text-sm text-slate-500">One view for ownership, follow-up, notification, and next action.</p>
        </div>
        <button type="button" onClick={() => void load()} title="Refresh Sales operations" className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {cards.map(([label, value, color]) => <div key={label} className="rounded-xl bg-slate-50 p-3"><p className="text-[10px] uppercase tracking-wide text-slate-400">{label}</p><p className={`mt-2 text-xl font-bold ${color}`}>{value}</p></div>)}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-y border-slate-100 py-3">
        <Filter className="h-4 w-4 text-slate-400" />
        <select aria-label="Queue status" value={status} onChange={(event) => setStatus(event.target.value)} className="rounded-lg border border-slate-200 px-2.5 py-2 text-xs text-slate-700"><option value="all">All statuses</option>{statuses.slice(1).map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <select aria-label="Ownership scope" value={scope} onChange={(event) => setScope(event.target.value)} className="rounded-lg border border-slate-200 px-2.5 py-2 text-xs text-slate-700"><option value="all">All ownership</option><option value="mine">My leads</option><option value="unassigned">Unassigned</option></select>
        <select aria-label="Lead source" value={source} onChange={(event) => setSource(event.target.value)} className="rounded-lg border border-slate-200 px-2.5 py-2 text-xs text-slate-700"><option value="all">All sources</option>{sources.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <select aria-label="Score range" value={score} onChange={(event) => setScore(event.target.value)} className="rounded-lg border border-slate-200 px-2.5 py-2 text-xs text-slate-700"><option value="all">All scores</option><option value="hot">Hot (85+)</option><option value="qualified">Qualified (70+)</option></select>
      </div>

      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1200px] text-left text-xs">
          <thead className="bg-slate-50 uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-3">Lead</th><th className="px-3 py-3">Source / score</th><th className="px-3 py-3">Origin</th><th className="px-3 py-3">Queue</th><th className="px-3 py-3">Owner</th><th className="px-3 py-3">Follow-up</th><th className="px-3 py-3">Notification</th><th className="px-3 py-3">Last action</th><th className="px-3 py-3">Next action</th><th className="px-3 py-3">Result</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {data.results.map((row) => <tr key={row.id} className="hover:bg-slate-50">
              <td className="px-3 py-3"><p className="font-semibold text-slate-900">{row.contact_name || row.contact_id}</p><p className="text-slate-500">{row.email || row.contact_id}</p></td>
              <td className="px-3 py-3"><p className="text-slate-700">{row.source || 'Unknown'}</p><p className="font-semibold text-slate-900">{row.score ?? '—'}</p></td>
              <td className="px-3 py-3 text-slate-600">{row.score_origin.replaceAll('_', ' ')}</td>
              <td className="px-3 py-3"><span className="rounded-full bg-slate-100 px-2 py-1 font-medium text-slate-700">{row.queue_status}</span></td>
              <td className="px-3 py-3 text-slate-600">{row.assigned_user_id ? <span className="inline-flex items-center gap-1"><UserRound className="h-3.5 w-3.5" /> Assigned</span> : 'Unassigned'}</td>
              <td className="px-3 py-3"><span className={row.follow_up_status === 'tagged' ? 'text-emerald-700' : 'text-slate-600'}>{row.follow_up_status}</span></td>
              <td className="px-3 py-3"><span className={row.notification_status === 'sent' ? 'text-emerald-700' : row.notification_status === 'failed' ? 'text-rose-700' : 'text-slate-600'}>{row.notification_status}</span>{row.notification_error && <p className="max-w-[150px] truncate text-rose-600" title={row.notification_error}>{row.notification_error}</p>}</td>
              <td className="px-3 py-3 text-slate-500">{row.last_action_at ? new Date(row.last_action_at).toLocaleString() : '—'}</td>
              <td className="px-3 py-3 font-medium text-slate-700">{row.next_action}</td>
              <td className="px-3 py-3">{row.error ? <span className="inline-flex items-center gap-1 text-rose-700"><AlertTriangle className="h-3.5 w-3.5" /> Error</span> : row.retry_available ? <span className="text-amber-700">Retry available</span> : <span className="inline-flex items-center gap-1 text-slate-500"><CheckCircle2 className="h-3.5 w-3.5" /> {row.execution_status || 'ok'}</span>} <span className="ml-1 inline-flex items-center gap-1 text-slate-400" title="GHL contact reference"><ExternalLink className="h-3 w-3" />{row.ghl_contact_reference}</span></td>
            </tr>)}
          </tbody>
        </table>
        {!data.results.length && !loading && <p className="p-6 text-center text-sm text-slate-500">No leads match the current filters.</p>}
      </div>
    </section>
  )
}
