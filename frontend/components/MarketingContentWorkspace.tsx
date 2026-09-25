'use client'

import { useEffect, useState } from 'react'
import { CalendarDays, CheckCircle2, Loader2, Megaphone, RefreshCw, Send, Sparkles } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type ContentItem = {
  id: string
  title: string
  content_type: string
  channel: string
  status: string
  content: string
  confidence: string
  due_at: string | null
  source_documents: Array<{ title?: string; source?: string | null }>
}

const statusOrder = ['all', 'draft', 'in_review', 'revision_required', 'approved', 'scheduled', 'published', 'rejected']

export default function MarketingContentWorkspace() {
  const { can } = usePermissions()
  const [items, setItems] = useState<ContentItem[]>([])
  const [status, setStatus] = useState('all')
  const [topic, setTopic] = useState('ENY Consulting expertise in business analysis and AI strategy')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const getHeaders = async (json = false): Promise<HeadersInit> => {
    const { data: { session } } = await supabase.auth.getSession()
    return { ...(json ? { 'Content-Type': 'application/json' } : {}), ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}) }
  }

  const load = async () => {
    setLoading(true)
    try {
      const query = status === 'all' ? '' : `?status=${encodeURIComponent(status)}`
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/content${query}`, { headers: await getHeaders(), credentials: 'include' })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load Marketing content')
      setItems(payload.items || [])
      setMessage(null)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load Marketing content')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [status])

  const generate = async () => {
    setGenerating(true)
    setMessage('Generating a reviewable weekly plan with Marketing-scoped Claude knowledge...')
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/content/generate-weekly?topic=${encodeURIComponent(topic)}`, { method: 'POST', headers: await getHeaders(), credentials: 'include' })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Content generation failed')
      setMessage(`Generated ${payload.count} draft${payload.count === 1 ? '' : 's'}. All drafts require review before approval.`)
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Content generation failed')
    } finally {
      setGenerating(false)
    }
  }

  const updateStatus = async (item: ContentItem, nextStatus: string) => {
    const endpoint = nextStatus === 'published' ? `/content/${item.id}/publish` : `/content/${item.id}/status`
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing${endpoint}`, {
      method: 'PATCH', headers: await getHeaders(true), credentials: 'include',
      body: JSON.stringify({ status: nextStatus, note: `Marketing workspace transition to ${nextStatus}.` }),
    })
    const payload = await response.json()
    if (!response.ok) { setMessage(typeof payload.detail === 'string' ? payload.detail : 'Status update failed'); return }
    setMessage(`Content moved to ${nextStatus}.`)
    await load()
  }

  return (
    <section className="space-y-5 rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-[10px] uppercase tracking-[0.22em] text-cyan-600">Marketing operating workspace</p><h2 className="mt-1 text-2xl font-semibold text-slate-950">Content calendar</h2><p className="mt-2 text-sm text-slate-500">Draft, review, approve, schedule, and publish from one audited queue.</p></div>
        <button type="button" onClick={() => void load()} title="Refresh Marketing content" className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </div>
      <div className="grid gap-3 rounded-xl border border-cyan-100 bg-cyan-50 p-4 lg:grid-cols-[1fr_auto]">
        <label className="block"><span className="mb-2 block text-xs font-semibold text-cyan-900">Weekly content topic</span><input value={topic} onChange={(event) => setTopic(event.target.value)} className="w-full rounded-lg border border-cyan-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-cyan-500" /></label>
        <button type="button" onClick={() => void generate()} disabled={generating || !can('marketing:write')} className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-50">{generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}{generating ? 'Generating...' : 'Generate weekly plan'}</button>
      </div>
      {message && <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{message}</p>}
      <div className="flex flex-wrap items-center gap-2 border-y border-slate-100 py-3"><Megaphone className="h-4 w-4 text-slate-400" />{statusOrder.map((value) => <button key={value} type="button" onClick={() => setStatus(value)} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${status === value ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>{value.replaceAll('_', ' ')}</button>)}</div>
      <div className="grid gap-3 lg:grid-cols-2">
        {items.map((item) => <article key={item.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4"><div className="flex items-start justify-between gap-3"><div><h3 className="font-semibold text-slate-900">{item.title}</h3><p className="mt-1 text-xs uppercase tracking-wide text-slate-500">{item.content_type.replaceAll('_', ' ')} · {item.channel} · {item.status}</p></div><span className="rounded-full bg-white px-2 py-1 text-[10px] font-semibold uppercase text-slate-500">{item.confidence}</span></div><p className="mt-3 line-clamp-4 whitespace-pre-wrap text-sm leading-6 text-slate-600">{item.content}</p><div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500"><span className="inline-flex items-center gap-1"><CalendarDays className="h-3.5 w-3.5" />{item.due_at ? new Date(item.due_at).toLocaleDateString() : 'No due date'}</span><span>{item.source_documents.length} source documents</span></div><div className="mt-3 flex flex-wrap gap-2">{item.status === 'draft' && can('marketing:write') && <button type="button" onClick={() => void updateStatus(item, 'in_review')} className="rounded-lg border border-cyan-200 px-2.5 py-1.5 text-xs font-semibold text-cyan-700">Submit review</button>}{item.status === 'in_review' && can('marketing:approve') && <button type="button" onClick={() => void updateStatus(item, 'approved')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-700"><CheckCircle2 className="h-3.5 w-3.5" />Approve</button>}{item.status === 'approved' && can('marketing:publish') && <button type="button" onClick={() => void updateStatus(item, 'published')} className="inline-flex items-center gap-1 rounded-lg border border-violet-200 px-2.5 py-1.5 text-xs font-semibold text-violet-700"><Send className="h-3.5 w-3.5" />Publish</button>}{item.status === 'in_review' && can('marketing:approve') && <button type="button" onClick={() => void updateStatus(item, 'revision_required')} className="rounded-lg border border-amber-200 px-2.5 py-1.5 text-xs font-semibold text-amber-700">Request revision</button>}</div></article>)}
      </div>
      {!items.length && !loading && <p className="py-8 text-center text-sm text-slate-500">No content matches this queue.</p>}
    </section>
  )
}
