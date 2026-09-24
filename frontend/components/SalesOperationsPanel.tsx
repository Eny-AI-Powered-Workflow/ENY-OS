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
  health?: {
    queue_health?: string
    crm_status?: string
  }
  sla?: {
    rules?: Record<string, number>
    alerts?: Array<{
      severity: string
      code: string
      message: string
      count: number
      action: string
    }>
  }
  reporting?: {
    response_compliance_percent?: number
    workflow_success_percent?: number
    closed_leads?: number
    average_response_minutes?: number
  }
  monitoring?: {
    lead_intake?: { today?: number; yesterday?: number; change_percent?: number | null }
    stale_leads?: number
    no_contact_aging?: Record<string, number>
    conversion_by_source?: Record<string, { total: number; contacted: number; qualified: number; closed: number; conversion_percent: number }>
    owner_workload?: Array<{ owner_id: string; total: number; active: number; stale: number }>
  }
  rollout?: {
    status?: string
    training_focus?: string
    open_alerts?: number
  }
  results: Operation[]
  quality?: { quality_status?: string; duplicate_groups?: unknown[]; contacts_checked?: number }
  adoption?: { policy?: { ownership?: string[]; follow_up?: string[]; escalation?: string[]; weekly_review?: string[] }; weekly_review?: { results_created?: number; audit_events?: number; open_escalations?: number; stale_active_work?: number } }
  performance?: { conversion_funnel?: Record<string, number>; hot_lead_aging?: Record<string, number>; blocked_queue?: Record<string, number>; exceptions?: Record<string, number> }
  persistentAlerts?: Array<{ id: string; type: string; severity: string; source: string; message: string; status: string; created_at: string | null }>
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
      const [qualityResponse, adoptionResponse, performanceResponse, alertsResponse] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/quality`, { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/adoption-policy`, { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/reporting`, { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/alerts`, { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' }),
      ])
      const quality = qualityResponse.ok ? await qualityResponse.json() : null
      const adoption = adoptionResponse.ok ? await adoptionResponse.json() : null
      const performance = performanceResponse.ok ? await performanceResponse.json() : null
      const persistentAlerts = alertsResponse.ok ? (await alertsResponse.json()).alerts || [] : []
      setData({ ...payload, quality: quality?.quality, adoption, performance, persistentAlerts })
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
  const alerts = data.sla?.alerts || []
  const reporting = data.reporting || {}
  const monitoring = data.monitoring || {}
  const intake = monitoring.lead_intake || {}
  const aging = monitoring.no_contact_aging || {}
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

      <div className="grid gap-3 border-y border-slate-100 py-4 md:grid-cols-4">
        {[
          ['SLA compliance', `${reporting.response_compliance_percent ?? 0}%`, 'text-cyan-700'],
          ['Workflow success', `${reporting.workflow_success_percent ?? 0}%`, 'text-emerald-700'],
          ['Closed leads', reporting.closed_leads ?? 0, 'text-slate-700'],
          ['Rollout status', data.rollout?.status === 'ready' ? 'Ready' : 'Needs attention', data.rollout?.status === 'ready' ? 'text-emerald-700' : 'text-amber-700'],
        ].map(([label, value, color]) => <div key={label} className="rounded-xl border border-slate-100 bg-white p-3"><p className="text-[10px] uppercase tracking-wide text-slate-400">{label}</p><p className={`mt-2 text-lg font-bold ${color}`}>{value}</p></div>)}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center justify-between gap-3">
            <div><p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">SLA alerting</p><h3 className="mt-1 text-sm font-semibold text-slate-900">Action queue</h3></div>
            <span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${data.health?.queue_health === 'healthy' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{data.health?.queue_health || 'unknown'}</span>
          </div>
          <div className="mt-3 space-y-2">
            {alerts.length ? alerts.map((item) => <div key={item.code} className="flex items-start gap-3 rounded-lg border border-white bg-white p-3"><AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${item.severity === 'critical' ? 'text-rose-600' : 'text-amber-600'}`} /><div className="min-w-0"><p className="text-xs font-semibold text-slate-800">{item.message} <span className="text-slate-400">({item.count})</span></p><p className="mt-1 text-xs text-slate-500">{item.action}</p></div></div>) : <p className="text-xs text-slate-500">No active SLA alerts in the current queue.</p>}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Team adoption</p>
          <h3 className="mt-1 text-sm font-semibold text-slate-900">Rollout focus</h3>
          <p className="mt-3 text-sm leading-6 text-slate-600">{data.rollout?.training_focus || 'Use the queue controls to manage the next action.'}</p>
          <p className="mt-3 text-xs text-slate-400">CRM: {data.health?.crm_status || 'unknown'} · Open alerts: {data.rollout?.open_alerts ?? alerts.length}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Daily intake</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">{intake.today ?? 0}</p>
          <p className="mt-1 text-xs text-slate-500">New leads today · yesterday {intake.yesterday ?? 0}{intake.change_percent !== null && intake.change_percent !== undefined ? ` · ${intake.change_percent}% change` : ''}</p>
          <p className="mt-4 text-xs font-semibold text-rose-700">Stale leads: {monitoring.stale_leads ?? 0}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">No-contact aging</p>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
            <span>&lt; 1h <strong className="float-right text-slate-900">{aging.under_1_hour ?? 0}</strong></span>
            <span>1-4h <strong className="float-right text-slate-900">{aging.one_to_four_hours ?? 0}</strong></span>
            <span>4-24h <strong className="float-right text-amber-700">{aging.four_to_twenty_four_hours ?? 0}</strong></span>
            <span>&gt; 24h <strong className="float-right text-rose-700">{aging.over_24_hours ?? 0}</strong></span>
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Owner workload</p>
          <div className="mt-3 space-y-2 text-xs">
            {(monitoring.owner_workload || []).slice(0, 4).map((owner) => <div key={owner.owner_id} className="flex items-center justify-between gap-3 text-slate-600"><span className="truncate">{owner.owner_id === 'unassigned' ? 'Unassigned' : `${owner.owner_id.slice(0, 8)}...`}</span><span className="font-semibold text-slate-900">{owner.active} active <span className={owner.stale ? 'text-rose-700' : 'text-slate-400'}>({owner.stale} stale)</span></span></div>)}
            {!monitoring.owner_workload?.length && <span className="text-slate-500">No assigned workload.</span>}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Conversion by source</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(monitoring.conversion_by_source || {}).map(([sourceName, sourceData]) => <div key={sourceName} className="rounded-lg bg-slate-50 p-3"><div className="flex items-center justify-between gap-2"><span className="truncate text-xs font-semibold text-slate-800">{sourceName}</span><span className="text-xs font-bold text-emerald-700">{sourceData.conversion_percent}%</span></div><p className="mt-1 text-[11px] text-slate-500">{sourceData.total} total · {sourceData.contacted} contacted · {sourceData.closed} closed</p></div>)}
          {!Object.keys(monitoring.conversion_by_source || {}).length && <p className="text-xs text-slate-500">No source data available.</p>}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">CRM quality</p>
          <div className="mt-2 flex flex-wrap items-center gap-3"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${data.quality?.quality_status === 'healthy' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{data.quality?.quality_status || 'not checked'}</span><span className="text-xs text-slate-500">{data.quality?.contacts_checked ?? 0} contacts checked</span><span className="text-xs text-slate-500">{data.quality?.duplicate_groups?.length ?? 0} duplicate groups</span></div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Weekly review</p>
          <p className="mt-2 text-xs leading-5 text-slate-600">{data.adoption?.policy?.weekly_review?.[0] || 'Review the queue and open alerts every week.'}</p>
          <p className="mt-2 text-xs text-slate-500">{data.adoption?.weekly_review?.audit_events ?? 0} audit events · {data.adoption?.weekly_review?.open_escalations ?? 0} escalations · {data.adoption?.weekly_review?.stale_active_work ?? 0} stale active</p>
        </div>
      </div>

      {data.persistentAlerts?.length ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-4"><p className="text-[10px] uppercase tracking-[0.18em] text-rose-600">Hard failure alerts</p><div className="mt-2 space-y-2">{data.persistentAlerts.slice(0, 4).map((alert) => <div key={alert.id} className="flex items-start justify-between gap-3 text-xs"><span className="text-rose-800">{alert.message}</span><span className="shrink-0 font-semibold uppercase text-rose-600">{alert.source}</span></div>)}</div></div> : null}

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Performance review</p>
        <div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          <div><span className="text-slate-500">Funnel closed</span><strong className="float-right text-slate-900">{data.performance?.conversion_funnel?.closed ?? 0}</strong></div>
          <div><span className="text-slate-500">Hot &gt; 3 days</span><strong className="float-right text-rose-700">{data.performance?.hot_lead_aging?.over_3_days ?? 0}</strong></div>
          <div><span className="text-slate-500">Blocked</span><strong className="float-right text-amber-700">{(data.performance?.blocked_queue?.held ?? 0) + (data.performance?.blocked_queue?.escalated ?? 0)}</strong></div>
          <div><span className="text-slate-500">Exceptions</span><strong className="float-right text-slate-900">{(data.performance?.exceptions?.reassignments ?? 0) + (data.performance?.exceptions?.failed_events ?? 0)}</strong></div>
        </div>
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
