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
  revision: number
  requires_ceo_approval: boolean
  compliance_flags: string[]
  due_at: string | null
  source_documents: Array<{ title?: string; source?: string | null }>
}
type Delivery = { id: string; content_id: string; channel: string; provider: string; status: string; scheduled_at: string; recipient_count: number; error: string | null }

const statusOrder = ['all', 'draft', 'in_review', 'revision_required', 'approved', 'scheduled', 'published', 'rejected']

export default function MarketingContentWorkspace() {
  const { can } = usePermissions()
  const [items, setItems] = useState<ContentItem[]>([])
  const [status, setStatus] = useState('all')
  const [topic, setTopic] = useState('ENY Consulting expertise in business analysis and AI strategy')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [deliveries, setDeliveries] = useState<Delivery[]>([])

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
      const deliveriesResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/deliveries`, { headers: await getHeaders(), credentials: 'include' })
      if (deliveriesResponse.ok) setDeliveries((await deliveriesResponse.json()).deliveries || [])
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
    const note = window.prompt(nextStatus === 'rejected' || nextStatus === 'revision_required' ? `Reason for ${nextStatus.replaceAll('_', ' ')}:` : `Review note for ${nextStatus}:`)
    if (!note || note.trim().length < 3) return
    let endpoint = `/content/${item.id}/status`
    let method = 'PATCH'
    let body: BodyInit | undefined = JSON.stringify({ status: nextStatus, note })
    if (nextStatus === 'in_review') {
      endpoint = `/content/${item.id}/submit?note=${encodeURIComponent(note)}`
      method = 'POST'
      body = undefined
    } else if (nextStatus === 'approved' && item.requires_ceo_approval) {
      if (!can('marketing:approve_sensitive')) { setMessage('This item requires CEO approval.'); return }
      const approvalNote = window.prompt('CEO approval rationale and claim verification reference:')
      if (!approvalNote) return
      endpoint = `/content/${item.id}/approve-sensitive`
      method = 'POST'
      body = JSON.stringify({ approval_note: approvalNote, claims_verified: window.confirm('Confirm that the sensitive claims are supported by the attached source documents.') })
    }
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing${endpoint}`, {
      method, headers: await getHeaders(method === 'PATCH' || Boolean(body)), credentials: 'include', body,
    })
    const payload = await response.json()
    if (!response.ok) { setMessage(typeof payload.detail === 'string' ? payload.detail : 'Status update failed'); return }
    setMessage(`Content moved to ${nextStatus}.`)
    await load()
  }

  const editContent = async (item: ContentItem) => {
    const title = window.prompt('Edit title', item.title)
    if (!title) return
    const content = window.prompt('Edit content', item.content)
    if (!content) return
    const note = window.prompt('Revision note (required):')
    if (!note || note.trim().length < 3) return
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/content/${item.id}`, {
      method: 'PATCH', headers: await getHeaders(true), credentials: 'include', body: JSON.stringify({ title, content, note }),
    })
    const payload = await response.json()
    if (!response.ok) { setMessage(typeof payload.detail === 'string' ? payload.detail : 'Content edit failed'); return }
    setMessage(`Revision ${payload.revision} saved. Previous version is retained in history.`)
    await load()
  }

  const reviewBrand = async (item: ContentItem) => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/content/${item.id}/brand-review`, {
      method: 'POST', headers: await getHeaders(true), credentials: 'include', body: JSON.stringify({ note: 'Workspace brand and SOP review' }),
    })
    const payload = await response.json()
    setMessage(response.ok ? `Brand/SOP review: ${payload.status}. ${payload.issues?.length ? payload.issues.join('; ') : ''}` : (typeof payload.detail === 'string' ? payload.detail : 'Brand review failed'))
    await load()
  }

  const schedule = async (item: ContentItem) => {
    const channel = window.prompt('Channel: email, linkedin, instagram, facebook, x, or tiktok', item.channel)
    if (!channel) return
    const scheduledAt = window.prompt('Scheduled time (ISO format)', new Date(Date.now() + 60 * 60 * 1000).toISOString())
    if (!scheduledAt) return
    const sensitive = can('marketing:approve_sensitive') && window.confirm('Is this a sensitive broadcast requiring CEO approval?')
    const ceoApprovalNote = sensitive ? window.prompt('CEO approval reference or note') || '' : undefined
    const recipients = channel === 'email'
      ? (window.prompt('Recipients as contact_id,email pairs separated by commas') || '').split(',').map((value) => { const [contact_id, email] = value.trim().split(':'); return contact_id && email ? { contact_id, email } : null }).filter(Boolean)
      : []
    const consentConfirmed = channel !== 'email' || window.confirm('Confirm that every listed recipient has valid marketing consent.')
    if (channel === 'email' && !consentConfirmed) return
    const consentEvidence = channel === 'email' ? window.prompt('Record the consent source or GHL consent field used to verify recipients:') : undefined
    if (channel === 'email' && !consentEvidence) return
    const consentedRecipients = recipients.map((recipient) => ({ ...recipient, consent_confirmed: true }))
    const unsubscribeUrl = channel === 'email' ? window.prompt('HTTPS unsubscribe URL') : undefined
    if (channel === 'email' && !unsubscribeUrl) return
    const endpoint = sensitive ? 'schedule-sensitive' : 'schedule'
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/deliveries/${endpoint}`, { method: 'POST', headers: await getHeaders(true), credentials: 'include', body: JSON.stringify({ content_id: item.id, channel, scheduled_at: scheduledAt, recipients: consentedRecipients, subject: item.title, unsubscribe_url: unsubscribeUrl, consent_confirmed: consentConfirmed, consent_evidence: consentEvidence, sensitive_broadcast: sensitive, ceo_approval_note: ceoApprovalNote }) })
    const payload = await response.json()
    setMessage(response.ok ? `Delivery scheduled through ${payload.provider}.` : (typeof payload.detail === 'string' ? payload.detail : 'Delivery scheduling failed'))
    await load()
  }

  const execute = async (delivery: Delivery) => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/deliveries/${delivery.id}/execute`, { method: 'POST', headers: await getHeaders(), credentials: 'include' })
    const payload = await response.json()
    setMessage(response.ok ? `Delivery ${payload.status}.` : (typeof payload.detail === 'string' ? payload.detail : 'Delivery failed'))
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
        {items.map((item) => <article key={item.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4"><div className="flex items-start justify-between gap-3"><div><h3 className="font-semibold text-slate-900">{item.title}</h3><p className="mt-1 text-xs uppercase tracking-wide text-slate-500">{item.content_type.replaceAll('_', ' ')} · {item.channel} · {item.status}</p></div><span className="rounded-full bg-white px-2 py-1 text-[10px] font-semibold uppercase text-slate-500">{item.confidence}</span></div><p className="mt-3 line-clamp-4 whitespace-pre-wrap text-sm leading-6 text-slate-600">{item.content}</p><div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500"><span className="inline-flex items-center gap-1"><CalendarDays className="h-3.5 w-3.5" />{item.due_at ? new Date(item.due_at).toLocaleDateString() : 'No due date'}</span><span>{item.source_documents.length} source documents</span></div><div className="mt-3 flex flex-wrap gap-2">{item.status === 'draft' && can('marketing:write') && <button type="button" onClick={() => void updateStatus(item, 'in_review')} className="rounded-lg border border-cyan-200 px-2.5 py-1.5 text-xs font-semibold text-cyan-700">Submit review</button>}{item.status === 'in_review' && can('marketing:approve') && <button type="button" onClick={() => void updateStatus(item, 'approved')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-700"><CheckCircle2 className="h-3.5 w-3.5" />Approve</button>}{item.status === 'approved' && can('marketing:send') && <button type="button" onClick={() => void schedule(item)} className="inline-flex items-center gap-1 rounded-lg border border-violet-200 px-2.5 py-1.5 text-xs font-semibold text-violet-700"><Send className="h-3.5 w-3.5" />Schedule delivery</button>}{item.status === 'in_review' && can('marketing:approve') && <button type="button" onClick={() => void updateStatus(item, 'revision_required')} className="rounded-lg border border-amber-200 px-2.5 py-1.5 text-xs font-semibold text-amber-700">Request revision</button>}</div></article>)}
      </div>
      <div className="space-y-2">
        {items.filter((item) => item.status === 'revision_required' || item.status === 'rejected' || item.status === 'scheduled' || item.status === 'in_review').map((item) => <div key={`governance-${item.id}`} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-xs">
          <span className="min-w-0 flex-1 text-slate-600"><strong className="text-slate-800">{item.title}</strong>{item.requires_ceo_approval && <span className="ml-2 text-rose-700">CEO claim review required: {item.compliance_flags.join(', ')}</span>}</span>
          <div className="flex flex-wrap gap-2">
            {(item.status === 'revision_required' || item.status === 'rejected') && can('marketing:write') && <><button type="button" onClick={() => void editContent(item)} className="rounded-md border border-slate-200 px-2 py-1 font-semibold text-slate-700">Edit revision</button><button type="button" onClick={() => void updateStatus(item, 'in_review')} className="rounded-md border border-cyan-200 px-2 py-1 font-semibold text-cyan-700">Resubmit</button></>}
            {item.status === 'in_review' && can('marketing:approve') && <button type="button" onClick={() => void updateStatus(item, 'rejected')} className="rounded-md border border-rose-200 px-2 py-1 font-semibold text-rose-700">Reject with reason</button>}
            {item.status === 'in_review' && item.requires_ceo_approval && can('marketing:approve_sensitive') && <button type="button" onClick={() => void updateStatus(item, 'approved')} className="rounded-md border border-emerald-200 px-2 py-1 font-semibold text-emerald-700">CEO approve</button>}
            {item.status === 'scheduled' && can('marketing:publish') && <button type="button" onClick={() => void updateStatus(item, 'published')} className="rounded-md border border-emerald-200 px-2 py-1 font-semibold text-emerald-700">Record publication</button>}
            {can('marketing:research') && <button type="button" onClick={() => void reviewBrand(item)} className="rounded-md border border-amber-200 px-2 py-1 font-semibold text-amber-800">Brand/SOP review</button>}
          </div>
        </div>)}
      </div>
      {!items.length && !loading && <p className="py-8 text-center text-sm text-slate-500">No content matches this queue.</p>}
      <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center justify-between gap-3"><h3 className="font-semibold text-slate-900">Delivery tracking</h3><span className="text-xs text-slate-500">GHL email · Buffer social</span></div><div className="mt-3 space-y-2">{deliveries.length ? deliveries.slice(0, 8).map((delivery) => <div key={delivery.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 p-3 text-xs"><span className="font-medium text-slate-700">{delivery.channel} · {delivery.provider} · {delivery.status}</span><span className={delivery.error ? 'text-rose-700' : 'text-slate-500'}>{delivery.error || `${delivery.recipient_count} recipients`}</span>{delivery.status === 'scheduled' && can('marketing:send') && <button type="button" onClick={() => void execute(delivery)} className="rounded-lg border border-cyan-200 px-2 py-1 font-semibold text-cyan-700">Execute</button>}</div>) : <p className="text-xs text-slate-500">No delivery records yet.</p>}</div></div>
    </section>
  )
}
