'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, BarChart3, CheckCircle2, CircleSlash2, Eye, RefreshCw, Search, Users } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type SourceStatus = { status: string; configured_sources: string[] }
type SeoOverview = { source_status: SourceStatus; counts: { observations: number; keywords: number }; latest_by_type: Record<string, { source: string; observed_at: string; value: Record<string, unknown> }> }
type SocialMention = { id: string; platform: string; text: string; matched_term: string; classification: string; sentiment: string; risk_level: string; source: string; observed_at: string }
type SocialOverview = { source_status: SourceStatus; counts: { mentions: number; open_high_risk: number; classifications: Record<string, number>; risk: Record<string, number> }; mentions: SocialMention[] }

export default function MarketingIntelligence() {
  const { can } = usePermissions()
  const canSeo = can('marketing:seo')
  const canSocial = can('marketing:social')
  const [seo, setSeo] = useState<SeoOverview | null>(null)
  const [social, setSocial] = useState<SocialOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const headers: HeadersInit = session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}
      const base = process.env.NEXT_PUBLIC_API_URL
      const responses = await Promise.all([
        canSeo ? fetch(`${base}/api/v1/marketing/seo/overview`, { headers, credentials: 'include' }) : Promise.resolve(null),
        canSocial ? fetch(`${base}/api/v1/marketing/social/overview`, { headers, credentials: 'include' }) : Promise.resolve(null),
      ])
      if (responses[0]?.ok) setSeo(await responses[0].json())
      if (responses[1]?.ok) setSocial(await responses[1].json())
      if (!responses.some((response) => response?.ok)) setMessage('No Marketing intelligence permissions are available for this account.')
      else setMessage(null)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load Marketing intelligence')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [canSeo, canSocial])

  const statusBadge = (status?: string) => status === 'configured'
    ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700"><CheckCircle2 className="h-3.5 w-3.5" />Source connected</span>
    : <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500"><CircleSlash2 className="h-3.5 w-3.5" />Not configured</span>

  return (
    <section className="space-y-5 rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-[10px] uppercase tracking-[0.22em] text-amber-700">Evidence-led visibility</p><h2 className="mt-1 text-2xl font-semibold text-slate-950">SEO & social listening</h2><p className="mt-2 text-sm text-slate-500">Only ingested observations appear as metrics. Every result keeps its provider and timestamp.</p></div>
        <button type="button" onClick={() => void load()} title="Refresh intelligence" className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </div>
      {message && <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">{message}</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-start justify-between gap-3"><div className="flex items-center gap-2"><Search className="h-4 w-4 text-amber-700" /><h3 className="font-semibold text-slate-900">SEO visibility</h3></div>{statusBadge(seo?.source_status.status)}</div>
          <div className="mt-4 grid grid-cols-2 gap-3"><div className="rounded-lg bg-white p-3"><p className="text-xs text-slate-500">Tracked keywords</p><p className="mt-1 text-2xl font-semibold text-slate-950">{seo?.counts.keywords ?? '—'}</p></div><div className="rounded-lg bg-white p-3"><p className="text-xs text-slate-500">Source observations</p><p className="mt-1 text-2xl font-semibold text-slate-950">{seo?.counts.observations ?? '—'}</p></div></div>
          <div className="mt-4 space-y-2">{Object.entries(seo?.latest_by_type || {}).slice(0, 4).map(([type, item]) => <div key={type} className="flex items-center justify-between gap-3 border-t border-slate-200 pt-2 text-xs"><span className="font-medium text-slate-700">{type.replaceAll('_', ' ')}</span><span className="text-right text-slate-500">{item.source} · {new Date(item.observed_at).toLocaleDateString()}</span></div>)}{!loading && !Object.keys(seo?.latest_by_type || {}).length && <p className="text-xs text-slate-500">No source-backed SEO observations yet.</p>}</div>
        </article>
        <article className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-start justify-between gap-3"><div className="flex items-center gap-2"><Eye className="h-4 w-4 text-rose-700" /><h3 className="font-semibold text-slate-900">Social listening</h3></div>{statusBadge(social?.source_status.status)}</div>
          <div className="mt-4 grid grid-cols-3 gap-3"><div className="rounded-lg bg-white p-3"><p className="text-xs text-slate-500">Mentions</p><p className="mt-1 text-2xl font-semibold text-slate-950">{social?.counts.mentions ?? '—'}</p></div><div className="rounded-lg bg-white p-3"><p className="text-xs text-slate-500">High risk open</p><p className="mt-1 text-2xl font-semibold text-rose-700">{social?.counts.open_high_risk ?? '—'}</p></div><div className="rounded-lg bg-white p-3"><p className="text-xs text-slate-500">Platforms</p><p className="mt-1 text-2xl font-semibold text-slate-950">{social ? new Set(social.mentions.map((item) => item.platform)).size : '—'}</p></div></div>
          <div className="mt-4 space-y-2">{(social?.mentions || []).slice(0, 3).map((mention) => <div key={mention.id} className="border-t border-slate-200 pt-2"><div className="flex items-center justify-between gap-2 text-xs"><span className="font-semibold text-slate-700">{mention.platform} · {mention.classification.replaceAll('_', ' ')}</span><span className={mention.risk_level === 'high' || mention.risk_level === 'critical' ? 'font-semibold text-rose-700' : 'text-slate-500'}>{mention.risk_level} risk</span></div><p className="mt-1 line-clamp-2 text-xs text-slate-600">{mention.text}</p><p className="mt-1 text-[10px] text-slate-400">{mention.source} · {new Date(mention.observed_at).toLocaleString()}</p></div>)}{!loading && !social?.mentions.length && <p className="text-xs text-slate-500">No mentions have been ingested yet.</p>}</div>
        </article>
      </div>
      <div className="flex flex-wrap gap-3 border-t border-slate-100 pt-3 text-xs text-slate-500"><span className="inline-flex items-center gap-1"><BarChart3 className="h-3.5 w-3.5" />Source-backed metrics</span><span className="inline-flex items-center gap-1"><Users className="h-3.5 w-3.5" />Human review for risk</span><span className="inline-flex items-center gap-1"><AlertTriangle className="h-3.5 w-3.5" />No automatic replies</span></div>
    </section>
  )
}
