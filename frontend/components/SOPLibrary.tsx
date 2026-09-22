'use client'

import { useEffect, useState } from 'react'
import { BookOpen, CheckCircle2, Clock3, FileStack, Loader2, RefreshCw, Trash2 } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type SOP = {
  title: string
  department: string
  source: string
  chunks: number
  created_at: string | null
  updated_at: string | null
  is_active: boolean
}

const departmentNames: Record<string, string> = {
  enrollment: 'Sales & Enrollment',
  ceo: 'CEO',
  programs_manager: 'Program Management',
  customer_success: 'Customer Success',
  business_support: 'Business Support',
  executive_assistant: 'Executive Assistant',
  developer: 'Platform Engineering',
}

export default function SOPLibrary() {
  const { can } = usePermissions()
  const [documents, setDocuments] = useState<SOP[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ai/knowledge/documents`, {
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        credentials: 'include',
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load SOP library')
      setDocuments(payload.documents || [])
      setMessage(null)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load SOP library')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (can('agents:configure')) void load()
  }, [can('agents:configure')])

  if (!can('agents:configure')) return null

  const remove = async (document: SOP) => {
    const confirmed = window.confirm(`Delete "${document.title}" from ${departmentNames[document.department] || document.department}?`)
    if (!confirmed) return
    setDeleting(`${document.title}:${document.department}`)
    setMessage(null)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const params = new URLSearchParams({ title: document.title, department: document.department })
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ai/knowledge/documents?${params.toString()}`, {
        method: 'DELETE',
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        credentials: 'include',
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to delete SOP')
      setMessage(`Deleted ${payload.chunks} knowledge chunk${payload.chunks === 1 ? '' : 's'}.`)
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to delete SOP')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <section className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-[0_22px_55px_rgba(15,23,42,0.08)]">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 bg-[radial-gradient(circle_at_top_right,_rgba(14,165,233,0.12),_transparent_32%)] px-6 py-5">
        <div className="flex items-center gap-3"><div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-100 text-sky-700"><BookOpen className="h-5 w-5" /></div><div><p className="text-[10px] uppercase tracking-[0.22em] text-sky-600">AI knowledge</p><h2 className="mt-1 text-xl font-semibold text-slate-950">Uploaded SOP library</h2></div></div>
        <button type="button" onClick={() => void load()} title="Refresh SOP library" className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-white"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </div>
      {message && <p className="mx-6 mt-4 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{message}</p>}
      <div className="divide-y divide-slate-100">
        {loading ? <div className="flex items-center gap-2 px-6 py-8 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" /> Loading knowledge library...</div> : documents.length === 0 ? <div className="px-6 py-10 text-center"><FileStack className="mx-auto h-8 w-8 text-slate-300" /><p className="mt-3 text-sm font-medium text-slate-700">No SOPs uploaded yet</p><p className="mt-1 text-xs text-slate-500">Published SOPs will appear here by department.</p></div> : documents.map((document) => <div key={`${document.title}:${document.department}`} className="flex flex-col gap-4 px-6 py-5 transition hover:bg-slate-50/70 md:flex-row md:items-center md:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="truncate font-semibold text-slate-900">{document.title}</h3><span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-700"><CheckCircle2 className="h-3 w-3" /> Active</span></div><div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500"><span>{departmentNames[document.department] || document.department}</span><span className="inline-flex items-center gap-1"><FileStack className="h-3.5 w-3.5" /> {document.chunks} chunks</span><span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" /> {document.updated_at ? new Date(document.updated_at).toLocaleDateString() : 'Unknown date'}</span></div><p className="mt-1 truncate text-xs text-slate-400">{document.source}</p></div><button type="button" onClick={() => void remove(document)} disabled={deleting === `${document.title}:${document.department}`} title="Delete SOP and its AI knowledge chunks" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700 transition hover:bg-rose-50 disabled:opacity-50">{deleting === `${document.title}:${document.department}` ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />} Delete</button></div>)}
      </div>
    </section>
  )
}
