'use client'

import { FormEvent, useEffect, useState } from 'react'
import { CheckCircle2, Clock3, FileText, Loader2, RefreshCw, ShieldCheck } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type Audience = 'shared' | 'marketing' | 'programs' | 'student_success'
type FoundationDocument = {
  id: string
  document_key: string
  title: string
  category: string
  audience: Audience
  status: 'draft' | 'in_review' | 'approved' | 'archived'
  source_status: 'unverified' | 'verified'
  source_reference: string | null
  content: string
  metadata: Record<string, unknown>
  version: number
  authoritative: boolean
  approved_at: string | null
  updated_at: string | null
}
type History = { versions: Array<{ version: number; snapshot: Record<string, unknown>; change_note: string; created_at: string | null }>; events: Array<{ event_type: string; details: Record<string, unknown>; created_at: string | null }> }

const audienceLabels: Record<Audience, string> = { shared: 'Shared', marketing: 'Marketing', programs: 'Programs', student_success: 'Student Success' }

export default function GraphicDesignerWorkspace() {
  const { can } = usePermissions()
  const [documents, setDocuments] = useState<FoundationDocument[]>([])
  const [permissions, setPermissions] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [selectedHistory, setSelectedHistory] = useState<{ title: string; history: History } | null>(null)
  const [documentKey, setDocumentKey] = useState('')
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('visual_identity')
  const [audience, setAudience] = useState<Audience>('marketing')
  const [content, setContent] = useState('')
  const [sourceReference, setSourceReference] = useState('')

  const headers = async (json = false): Promise<HeadersInit> => {
    const { data: { session } } = await supabase.auth.getSession()
    return { ...(json ? { 'Content-Type': 'application/json' } : {}), ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}) }
  }

  const load = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/foundation`, { headers: await headers(), credentials: 'include' })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load the design foundation')
      setDocuments(payload.documents || [])
      setPermissions(payload.permissions || [])
      setMessage(null)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load the design foundation')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const createDocument = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/foundation`, {
        method: 'POST', headers: await headers(true), credentials: 'include',
        body: JSON.stringify({ document_key: documentKey.trim().toLowerCase().replaceAll(' ', '-'), title, category, audience, content, source_reference: sourceReference || null }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to create foundation document')
      setMessage('Draft created as unverified. It is not available as authoritative guidance until approved.')
      setDocumentKey(''); setTitle(''); setContent(''); setSourceReference('')
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to create foundation document')
    } finally {
      setSaving(false)
    }
  }

  const updateDocument = async (document: FoundationDocument) => {
    const nextTitle = window.prompt('Document title', document.title)
    if (!nextTitle) return
    const nextContent = window.prompt('Guidance content', document.content)
    if (!nextContent) return
    const nextSource = window.prompt('Authoritative source reference (URL, approved file, or named owner)', document.source_reference || '')
    const changeNote = window.prompt('Change note (required)')
    if (!changeNote || changeNote.trim().length < 3) return
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/foundation/${document.id}`, {
      method: 'PATCH', headers: await headers(true), credentials: 'include',
      body: JSON.stringify({ title: nextTitle, content: nextContent, source_reference: nextSource || null, change_note: changeNote }),
    })
    const payload = await response.json()
    setMessage(response.ok ? `Version ${payload.version} saved as an unverified draft.` : (typeof payload.detail === 'string' ? payload.detail : 'Unable to save revision'))
    await load()
  }

  const submitForReview = async (document: FoundationDocument) => {
    const note = window.prompt('Note for the audience reviewer:')
    if (!note || note.trim().length < 3) return
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/foundation/${document.id}/submit?note=${encodeURIComponent(note)}`, { method: 'POST', headers: await headers(), credentials: 'include' })
    const payload = await response.json()
    setMessage(response.ok ? 'Submitted to the audience reviewer. Guidance remains non-authoritative until approved.' : (typeof payload.detail === 'string' ? payload.detail : 'Unable to submit document'))
    await load()
  }

  const reviewDocument = async (document: FoundationDocument, decision: 'approve' | 'changes') => {
    const isMarketing = document.audience === 'marketing' || document.audience === 'shared'
    const endpoint = decision === 'approve'
      ? `/api/v1/designer/foundation/${document.id}/approve-${isMarketing ? 'marketing' : 'programs'}`
      : `/api/v1/designer/foundation/${document.id}/request-${isMarketing ? 'marketing' : 'program'}-changes`
    const url = `${process.env.NEXT_PUBLIC_API_URL}${endpoint}`
    const note = window.prompt(decision === 'approve' ? 'Approval note and source verification details:' : 'Required changes (reason):')
    if (!note || note.trim().length < 5) return
    const body = decision === 'approve'
      ? { approval_note: note, source_verified: window.confirm('Confirm the cited source is authoritative, current, and approved for this audience.') }
      : { note }
    const response = await fetch(url, {
      method: 'POST', headers: await headers(true), credentials: 'include', body: JSON.stringify(body),
    })
    const payload = await response.json()
    setMessage(response.ok ? (decision === 'approve' ? 'Approved and source-verified for the selected audience.' : 'Returned to draft with the reviewer’s reason.') : (typeof payload.detail === 'string' ? payload.detail : 'Review action failed'))
    await load()
  }

  const showHistory = async (document: FoundationDocument) => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/foundation/${document.id}/history`, { headers: await headers(), credentials: 'include' })
    const payload = await response.json()
    if (!response.ok) { setMessage(typeof payload.detail === 'string' ? payload.detail : 'Unable to load document history'); return }
    setSelectedHistory({ title: document.title, history: payload })
  }

  const canCreate = permissions.includes('design:write')
  const canManage = permissions.includes('design:manage')
  const reviewMarketing = permissions.includes('design:review_marketing')
  const reviewPrograms = permissions.includes('design:review_programs')

  return (
    <section className="space-y-5 rounded-[20px] border border-slate-200 bg-white p-5 text-slate-900 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-[10px] uppercase tracking-[0.2em] text-teal-700">Foundation and governance</p><h2 className="mt-1 text-2xl font-semibold">Brand and design system</h2><p className="mt-2 max-w-2xl text-sm text-slate-600">Create versioned guidance, cite its source, and route it to the Marketing or Programs owner. Unverified drafts never count as approved brand knowledge.</p></div>
        <button type="button" onClick={() => void load()} title="Refresh foundation" className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </div>
      {message && <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">{message}</p>}
      {canCreate && <form onSubmit={createDocument} className="grid gap-3 rounded-xl border border-teal-100 bg-teal-50/60 p-4 md:grid-cols-2">
        <label className="block"><span className="mb-1 block text-xs font-semibold">Document key</span><input required minLength={3} maxLength={100} value={documentKey} onChange={(event) => setDocumentKey(event.target.value)} placeholder="brand-colors-primary" className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
        <label className="block"><span className="mb-1 block text-xs font-semibold">Title</span><input required minLength={3} maxLength={240} value={title} onChange={(event) => setTitle(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
        <label className="block"><span className="mb-1 block text-xs font-semibold">Category</span><select value={category} onChange={(event) => setCategory(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">{['brand_voice', 'visual_identity', 'logo_usage', 'color_palette', 'typography', 'imagery', 'accessibility', 'offers_claims', 'audience', 'template_rules', 'funnel_guidelines', 'program_materials'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select></label>
        <label className="block"><span className="mb-1 block text-xs font-semibold">Audience</span><select value={audience} onChange={(event) => setAudience(event.target.value as Audience)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">{Object.entries(audienceLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="block md:col-span-2"><span className="mb-1 block text-xs font-semibold">Source reference</span><input value={sourceReference} onChange={(event) => setSourceReference(event.target.value)} maxLength={2000} placeholder="Approved file link, source owner, or policy reference" className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
        <label className="block md:col-span-2"><span className="mb-1 block text-xs font-semibold">Guidance</span><textarea required minLength={1} maxLength={50000} rows={5} value={content} onChange={(event) => setContent(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
        <div className="flex flex-wrap items-center justify-between gap-3 md:col-span-2"><p className="text-xs text-slate-500">New entries start as unverified drafts; approval requires a source reference.</p><button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-teal-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}Create draft</button></div>
      </form>}
      <div className="grid gap-3 lg:grid-cols-2">
        {documents.map((document) => {
          const canReview = document.status === 'in_review' && ((reviewMarketing && ['marketing', 'shared'].includes(document.audience)) || (reviewPrograms && ['programs', 'student_success', 'shared'].includes(document.audience)))
          return <article key={document.id} className="rounded-xl border border-slate-200 p-4">
            <div className="flex items-start justify-between gap-3"><div><h3 className="font-semibold">{document.title}</h3><p className="mt-1 text-xs uppercase text-slate-500">{document.category.replaceAll('_', ' ')} · {audienceLabels[document.audience]} · v{document.version}</p></div><span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase ${document.authoritative ? 'bg-emerald-100 text-emerald-800' : document.status === 'in_review' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'}`}>{document.authoritative ? 'approved source' : `${document.status} · ${document.source_status}`}</span></div>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">{document.content}</p>
            {document.source_reference && <p className="mt-3 break-words text-xs text-slate-500">Source: {document.source_reference}</p>}
            <div className="mt-4 flex flex-wrap gap-2">
              {canManage && (document.status === 'draft' || document.status === 'in_review') && <button type="button" onClick={() => void updateDocument(document)} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold">Edit / version</button>}
              {canManage && document.status === 'draft' && <button type="button" onClick={() => void submitForReview(document)} className="rounded-md border border-cyan-200 px-2.5 py-1.5 text-xs font-semibold text-cyan-800">Submit for review</button>}
              {canReview && <button type="button" onClick={() => void reviewDocument(document, 'approve')} className="inline-flex items-center gap-1 rounded-md border border-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-800"><CheckCircle2 className="h-3.5 w-3.5" />Approve source</button>}
              {canReview && <button type="button" onClick={() => void reviewDocument(document, 'changes')} className="rounded-md border border-amber-200 px-2.5 py-1.5 text-xs font-semibold text-amber-800">Request changes</button>}
              <button type="button" onClick={() => void showHistory(document)} className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700"><Clock3 className="h-3.5 w-3.5" />History</button>
            </div>
            {document.authoritative && <p className="mt-3 inline-flex items-center gap-1 text-[10px] text-emerald-700"><ShieldCheck className="h-3.5 w-3.5" />Approved source for {audienceLabels[document.audience]}</p>}
          </article>
        })}
      </div>
      {!documents.length && !loading && <p className="py-8 text-center text-sm text-slate-500">No design foundation entries are available to this role yet.</p>}
      {selectedHistory && <div className="rounded-xl border border-slate-200 bg-slate-50 p-4"><div className="flex items-center justify-between gap-3"><h3 className="font-semibold">History · {selectedHistory.title}</h3><button type="button" onClick={() => setSelectedHistory(null)} className="rounded-md border border-slate-200 px-2 py-1 text-xs">Close</button></div><div className="mt-3 space-y-2">{selectedHistory.history.versions.map((version) => <div key={version.version} className="rounded-lg bg-white p-3 text-xs"><p className="font-semibold">Version {version.version} · {version.change_note}</p><p className="mt-1 whitespace-pre-wrap text-slate-600">{String(version.snapshot.content || '')}</p></div>)}{selectedHistory.history.events.map((event, index) => <div key={`${event.event_type}-${index}`} className="border-t border-slate-200 pt-2 text-xs text-slate-500">{event.event_type.replaceAll('_', ' ')} · {event.created_at ? new Date(event.created_at).toLocaleString() : ''} {typeof event.details.note === 'string' ? `· ${event.details.note}` : ''}</div>)}</div></div>}
    </section>
  )
}
