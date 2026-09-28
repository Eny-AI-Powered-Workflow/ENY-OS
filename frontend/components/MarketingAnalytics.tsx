'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Activity, RefreshCw } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'

type Metric = { status: string; value: number | null; provider: string | null; source: string | null; observed_at: string | null }
type Analytics = {
  observed_at: string
  status: string
  metrics: Record<string, Metric>
  campaigns: Array<{ name: string; metrics: Record<string, number>; sources: string[]; observed_at: string }>
  attribution: {
    leads_by_campaign: { status: string; source: string; observed_at: string | null; items: Array<{ campaign: string; leads: number }> }
    lead_sources: { status: string; source: string; observed_at: string | null; items: Array<{ source: string; leads: number }> }
    pipeline_contribution: { status: string; source: string; observed_at: string | null; items: Array<{ campaign: string; opportunities: number; value: number }> }
  }
  email_sends: { status: string; provider: string; records: number; recipients: number; sent: number; send_completion_rate: number | null; observed_at: string | null }
  sources: Record<string, string | number>
}

const metricLabels: Record<string, string> = {
  email_delivery_rate: 'Email delivery', email_open_rate: 'Email opens', email_click_rate: 'Email clicks',
  email_unsubscribe_rate: 'Unsubscribes', social_reach: 'Social reach', social_engagement: 'Social engagement',
  website_sessions: 'Website sessions', content_assisted_conversions: 'Content-assisted conversions',
  ghl_pipeline_value: 'GHL pipeline value', spend: 'Spend', attributed_revenue: 'Attributed revenue', roi: 'ROI',
}

export default function MarketingAnalytics() {
  const [report, setReport] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const headers: HeadersInit = session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/analytics`, { headers, credentials: 'include' })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load campaign analytics')
      setReport(payload)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load campaign analytics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const formatValue = (key: string, value: number | null | undefined) => {
    if (value === null || value === undefined) return 'Not configured'
    if (key.endsWith('_rate')) return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}%`
    if (key.includes('value') || key === 'spend' || key === 'attributed_revenue') return value.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }

  const sourceLine = (source?: string | null, observedAt?: string | null) => source && observedAt
    ? <p className="mt-1 text-[10px] text-slate-500">{source} · {new Date(observedAt).toLocaleString()}</p>
    : <p className="mt-1 text-[10px] text-slate-400">No provider observation received</p>

  const metrics = report?.metrics || {}
  const cards = ['email_delivery_rate', 'email_open_rate', 'email_click_rate', 'email_unsubscribe_rate', 'social_reach', 'social_engagement', 'website_sessions', 'content_assisted_conversions', 'ghl_pipeline_value', 'spend', 'attributed_revenue']

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-start justify-between gap-4 pb-4">
        <div><div className="flex items-center gap-2"><Activity className="h-4 w-4 text-emerald-700" /><h2 className="text-xl font-semibold">Campaign analytics & attribution</h2></div><p className="mt-1 text-xs text-muted-foreground">Provider-sourced metrics only. Missing integrations remain visibly unconfigured.</p></div>
        <button type="button" onClick={() => void load()} title="Refresh campaign analytics" className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-muted"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </CardHeader>
      <CardContent className="space-y-5">
        {error && <p className="rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">{error}</p>}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{cards.map((key) => {
          const metric = metrics[key]
          return <div key={key} className="rounded-lg border border-border bg-card p-3"><p className="text-xs text-muted-foreground">{metricLabels[key]}</p><p className="mt-2 text-xl font-semibold text-foreground">{loading ? '—' : formatValue(key, metric?.value)}</p>{sourceLine(metric?.source || metric?.provider, metric?.observed_at)}</div>
        })}</div>
        <div className="grid gap-4 lg:grid-cols-3">
          <section className="rounded-lg border border-border p-4"><h3 className="text-sm font-semibold">Leads by campaign</h3><p className="mt-1 text-xs text-muted-foreground">GoHighLevel attribution fields</p><div className="mt-3 space-y-2">{report?.attribution.leads_by_campaign.items.map((item) => <div key={item.campaign} className="flex justify-between gap-3 border-t border-border pt-2 text-xs"><span>{item.campaign}</span><strong>{item.leads.toLocaleString()}</strong></div>)}{!report?.attribution.leads_by_campaign.items.length && <p className="text-xs text-slate-500">Not configured or no campaign attribution data.</p>}</div>{sourceLine(report?.attribution.leads_by_campaign.source, report?.attribution.leads_by_campaign.observed_at)}</section>
          <section className="rounded-lg border border-border p-4"><h3 className="text-sm font-semibold">Lead sources</h3><p className="mt-1 text-xs text-muted-foreground">Live GHL contact source labels</p><div className="mt-3 space-y-2">{report?.attribution.lead_sources.items.slice(0, 6).map((item) => <div key={item.source} className="flex justify-between gap-3 border-t border-border pt-2 text-xs"><span>{item.source}</span><strong>{item.leads.toLocaleString()}</strong></div>)}{!report?.attribution.lead_sources.items.length && <p className="text-xs text-slate-500">{report?.attribution.lead_sources.status === 'connected' ? 'No source data returned.' : 'GoHighLevel not configured.'}</p>}</div>{sourceLine(report?.attribution.lead_sources.source, report?.attribution.lead_sources.observed_at)}</section>
          <section className="rounded-lg border border-border p-4"><h3 className="text-sm font-semibold">GHL pipeline contribution</h3><p className="mt-1 text-xs text-muted-foreground">Campaign-tagged opportunities only</p><div className="mt-3 space-y-2">{report?.attribution.pipeline_contribution.items.map((item) => <div key={item.campaign} className="border-t border-border pt-2 text-xs"><div className="flex justify-between gap-3"><span>{item.campaign}</span><strong>{item.opportunities} opp.</strong></div><p className="mt-1 text-muted-foreground">{item.value.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}</p></div>)}{!report?.attribution.pipeline_contribution.items.length && <p className="text-xs text-slate-500">No campaign-attributed pipeline data.</p>}</div>{sourceLine(report?.attribution.pipeline_contribution.source, report?.attribution.pipeline_contribution.observed_at)}</section>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="rounded-lg border border-border p-4"><h3 className="text-sm font-semibold">Email execution</h3><p className="mt-1 text-xs text-muted-foreground">GHL send log, not delivery/open tracking</p><div className="mt-3 grid grid-cols-2 gap-3 text-xs"><div><span className="text-muted-foreground">Records</span><p className="mt-1 text-lg font-semibold">{report?.email_sends.records ?? '—'}</p></div><div><span className="text-muted-foreground">Recipients / sent</span><p className="mt-1 text-lg font-semibold">{report ? `${report.email_sends.recipients} / ${report.email_sends.sent}` : '—'}</p></div><div className="col-span-2"><span className="text-muted-foreground">Send completion</span><p className="mt-1 font-semibold">{report?.email_sends.send_completion_rate === null || report?.email_sends.send_completion_rate === undefined ? 'Not configured' : `${report.email_sends.send_completion_rate}%`}</p></div></div>{sourceLine(report?.email_sends.provider, report?.email_sends.observed_at)}</section>
          <section className="rounded-lg border border-border p-4"><h3 className="text-sm font-semibold">Campaign observations</h3><div className="mt-3 space-y-2">{report?.campaigns.map((campaign) => <div key={campaign.name} className="border-t border-border pt-2"><div className="flex justify-between gap-3 text-xs"><strong>{campaign.name}</strong><span className="text-muted-foreground">{campaign.sources.join(', ')}</span></div><p className="mt-1 text-xs text-muted-foreground">{Object.entries(campaign.metrics).map(([key, value]) => `${metricLabels[key] || key}: ${formatValue(key, value)}`).join(' · ')}</p><p className="mt-1 text-[10px] text-slate-500">Observed {new Date(campaign.observed_at).toLocaleString()}</p></div>)}{!report?.campaigns.length && <p className="text-xs text-slate-500">No campaign metrics have been ingested.</p>}</div></section>
        </div>
        {report && <p className="border-t border-border pt-3 text-[10px] text-muted-foreground">Report assembled {new Date(report.observed_at).toLocaleString()} · integrations report not_configured until a source observation is received.</p>}
      </CardContent>
    </Card>
  )
}