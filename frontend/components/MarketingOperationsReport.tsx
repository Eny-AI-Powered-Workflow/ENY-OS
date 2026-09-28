'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, ClipboardCheck, RefreshCw } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type OperationsReport = {
  period_start: string
  period_end: string
  content_produced: number
  approval_turnaround_hours: number | null
  approval_turnaround_samples: number
  scheduled_publications: number
  published_content: number
  publication_completion_rate: number | null
  content_revision_rate: number | null
  pending_approvals: number
  overdue_approvals: Array<{ id: string; title: string; created_at: string }>
  seo_movement: Array<{ keyword: string; previous_position: number; latest_position: number; change: number; source: string; observed_at: string }>
  social_engagement: Array<{ campaign: string | null; value: number; source: string; observed_at: string }>
  email_performance: Record<string, Array<{ campaign: string | null; value: number; source: string; observed_at: string }>>
  campaign_performance: Array<{ campaign: string; metric: string; value: number; source: string; provider: string; observed_at: string }>
  failed_integrations: Array<{ type: string; source: string; message: string; severity: string; created_at: string | null }>
  open_alerts: Array<{ type: string; source: string; message: string; severity: string; created_at: string | null }>
  delivery_failures: number
  sop_adherence: { status: string; reviews: number; passed: number }
  brand_consistency: { status: string; reviews: number; consistent: number }
}

type WeeklyReview = { id: string; week_start: string; summary: string; created_at?: string; completed_at: string | null }

const emailLabels: Record<string, string> = {
  email_delivery_rate: 'Delivery rate', email_open_rate: 'Open rate', email_click_rate: 'Click rate', email_unsubscribe_rate: 'Unsubscribe rate',
}

export default function MarketingOperationsReport() {
  const { can } = usePermissions()
  const [report, setReport] = useState<OperationsReport | null>(null)
  const [reviews, setReviews] = useState<WeeklyReview[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [summary, setSummary] = useState('')
  const [decisions, setDecisions] = useState('')
  const [message, setMessage] = useState<string | null>(null)

  const getHeaders = async (json = false): Promise<HeadersInit> => {
    const { data: { session } } = await supabase.auth.getSession()
    return { ...(json ? { 'Content-Type': 'application/json' } : {}), ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}) }
  }

  const load = async () => {
    setLoading(true)
    try {
      const headers = await getHeaders()
      const base = process.env.NEXT_PUBLIC_API_URL
      const [reportResponse, reviewsResponse] = await Promise.all([
        fetch(`${base}/api/v1/marketing/operations/report`, { headers, credentials: 'include' }),
        fetch(`${base}/api/v1/marketing/operations/weekly-reviews`, { headers, credentials: 'include' }),
      ])
      const reportPayload = await reportResponse.json()
      if (!reportResponse.ok) throw new Error(typeof reportPayload.detail === 'string' ? reportPayload.detail : 'Unable to load Marketing operations report')
      setReport(reportPayload)
      if (reviewsResponse.ok) setReviews((await reviewsResponse.json()).reviews || [])
      setMessage(null)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load Marketing operations report')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const completeReview = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!summary.trim()) return
    setSaving(true)
    try {
      const now = new Date()
      const monday = new Date(now)
      monday.setDate(now.getDate() - ((now.getDay() + 6) % 7))
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/operations/weekly-review`, {
        method: 'POST', headers: await getHeaders(true), credentials: 'include',
        body: JSON.stringify({ week_start: monday.toISOString().slice(0, 10), summary, decisions: decisions.split('\n').map((item) => item.trim()).filter(Boolean) }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Weekly review could not be saved')
      setSummary('')
      setDecisions('')
      setMessage(`Weekly review recorded for ${payload.week_start}.`)
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Weekly review could not be saved')
    } finally {
      setSaving(false)
    }
  }

  const number = (value: number | null, suffix = '') => value === null ? 'Not configured' : `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`
  const cards = [
    ['Content produced', report?.content_produced],
    ['Approval turnaround', report?.approval_turnaround_hours === null ? null : report?.approval_turnaround_hours, ' h'],
    ['Publication completion', report?.publication_completion_rate, '%'],
    ['Content revision rate', report?.content_revision_rate, '%'],
    ['Pending approvals', report?.pending_approvals],
    ['Failed deliveries', report?.delivery_failures],
    ['SOP review adherence', report?.sop_adherence.status === 'measured' ? (report.sop_adherence.reviews ? report.sop_adherence.passed / report.sop_adherence.reviews * 100 : null) : null, '%'],
    ['Brand consistency', report?.brand_consistency.status === 'measured' ? (report.brand_consistency.reviews ? report.brand_consistency.consistent / report.brand_consistency.reviews * 100 : null) : null, '%'],
  ] as const

  return (
    <section className="space-y-5 rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-[10px] uppercase tracking-[0.22em] text-emerald-700">Marketing operating system</p><h2 className="mt-1 text-2xl font-semibold text-slate-950">Weekly operations</h2><p className="mt-2 text-sm text-slate-500">{report ? `${new Date(report.period_start).toLocaleDateString()} – ${new Date(report.period_end).toLocaleDateString()}` : 'Loading reporting period'}</p></div>
        <button type="button" onClick={() => void load()} title="Refresh operations report" className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </div>
      {message && <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">{message}</p>}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([label, value, suffix = '']) => <div key={label} className="rounded-lg border border-slate-200 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-xl font-semibold text-slate-950">{loading ? '—' : number(value ?? null, suffix)}</p></div>)}</div>
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-lg border border-slate-200 p-4"><h3 className="text-sm font-semibold">SEO movement</h3><div className="mt-3 space-y-2">{report?.seo_movement.map((item) => <div key={`${item.keyword}-${item.observed_at}`} className="border-t border-slate-100 pt-2 text-xs"><div className="flex justify-between gap-2"><span>{item.keyword}</span><strong>{item.change > 0 ? '+' : ''}{item.change} positions</strong></div><p className="mt-1 text-slate-500">{item.source} · {new Date(item.observed_at).toLocaleDateString()}</p></div>)}{!report?.seo_movement.length && <p className="text-xs text-slate-500">Not configured: two timestamped ranking observations are needed to calculate movement.</p>}</div></article>
        <article className="rounded-lg border border-slate-200 p-4"><h3 className="text-sm font-semibold">Email performance</h3><div className="mt-3 space-y-2">{Object.entries(report?.email_performance || {}).map(([key, values]) => <div key={key} className="border-t border-slate-100 pt-2 text-xs"><div className="flex justify-between gap-2"><span>{emailLabels[key] || key}</span><strong>{values.length ? `${values[0].value.toLocaleString()}%` : 'Not configured'}</strong></div>{values[0] && <p className="mt-1 text-slate-500">{values[0].source} · {new Date(values[0].observed_at).toLocaleString()}</p>}</div>)}</div></article>
        <article className="rounded-lg border border-slate-200 p-4"><h3 className="text-sm font-semibold">Campaign performance</h3><div className="mt-3 space-y-2">{report?.campaign_performance.slice(0, 6).map((metric, index) => <div key={`${metric.campaign}-${metric.metric}-${index}`} className="border-t border-slate-100 pt-2 text-xs"><div className="flex justify-between gap-2"><span>{metric.campaign} · {metric.metric.replaceAll('_', ' ')}</span><strong>{metric.value.toLocaleString()}</strong></div><p className="mt-1 text-slate-500">{metric.source} · {new Date(metric.observed_at).toLocaleDateString()}</p></div>)}{!report?.campaign_performance.length && <p className="text-xs text-slate-500">Not configured: no source-backed campaign observations.</p>}</div></article>
        <article className="rounded-lg border border-slate-200 p-4"><div className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-amber-700" /><h3 className="text-sm font-semibold">Open alerts</h3></div><div className="mt-3 space-y-2">{report?.open_alerts.map((alert, index) => <div key={`${alert.type}-${alert.source}-${index}`} className="border-t border-slate-100 pt-2 text-xs"><p className="font-semibold text-slate-800">{alert.type.replaceAll('_', ' ')} · {alert.source}</p><p className="mt-1 text-slate-600">{alert.message}</p></div>)}{!report?.open_alerts.length && <p className="inline-flex items-center gap-1 text-xs text-emerald-700"><CheckCircle2 className="h-3.5 w-3.5" />No open Marketing alerts</p>}</div></article>
      </div>
      <div className="grid gap-4 border-t border-slate-100 pt-4 lg:grid-cols-[1fr_1fr]">
        <form onSubmit={completeReview} className="space-y-3">
          <div className="flex items-center gap-2"><ClipboardCheck className="h-4 w-4 text-emerald-700" /><h3 className="text-sm font-semibold text-slate-900">Complete weekly review</h3></div>
          <label className="block"><span className="mb-1 block text-xs text-slate-600">Review summary</span><textarea value={summary} onChange={(event) => setSummary(event.target.value)} required minLength={10} maxLength={10000} rows={3} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-emerald-600" /></label>
          <label className="block"><span className="mb-1 block text-xs text-slate-600">Decisions and owners, one per line</span><textarea value={decisions} onChange={(event) => setDecisions(event.target.value)} rows={2} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-emerald-600" /></label>
          {can('marketing:configure') && <button type="submit" disabled={saving} className="rounded-lg bg-emerald-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? 'Recording...' : 'Record weekly review'}</button>}
          {!can('marketing:configure') && <p className="text-xs text-slate-500">Marketing lead or CEO permission is required to record the ritual.</p>}
        </form>
        <div><h3 className="text-sm font-semibold text-slate-900">Recent reviews</h3><div className="mt-3 space-y-2">{reviews.slice(0, 4).map((review) => <article key={review.id} className="rounded-lg bg-slate-50 p-3"><p className="text-xs font-semibold text-slate-700">Week of {new Date(review.week_start).toLocaleDateString()}</p><p className="mt-1 line-clamp-2 text-xs text-slate-600">{review.summary}</p></article>)}{!reviews.length && <p className="text-xs text-slate-500">No weekly reviews recorded yet.</p>}</div></div>
      </div>
    </section>
  )
}
