'use client'

import { ChangeEvent, useState } from 'react'
import { FileText, Loader2, UploadCloud } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'
import { API_TIMEOUTS, describeHttpError, describeRequestFailure, fetchWithTimeout } from '@/lib/api'

const departments = [
  ['enrollment', 'Sales & Enrollment'],
  ['ceo', 'CEO'],
  ['programs_manager', 'Program Management'],
  ['customer_success', 'Customer Success'],
  ['business_support', 'Business Support'],
  ['marketing', 'Marketing'],
  ['executive_assistant', 'Executive Assistant'],
  ['developer', 'Platform Engineering'],
] as const

export default function SOPPublisher() {
  const { can } = usePermissions()
  const [title, setTitle] = useState('')
  const [department, setDepartment] = useState('enrollment')
  const [source, setSource] = useState('ENY internal SOP')
  const [content, setContent] = useState('')
  const [fileName, setFileName] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [publishing, setPublishing] = useState(false)

  if (!can('agents:configure')) return null

  const loadTextFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.md') && !file.name.endsWith('.txt')) {
      setStatus('Use a Markdown or plain-text file for now. PDF and DOCX extraction is not enabled yet.')
      return
    }
    setContent(await file.text())
    setFileName(file.name)
    if (!title) setTitle(file.name.replace(/\.(md|txt)$/i, ''))
    setStatus(null)
  }

  const publish = async () => {
    if (!title.trim() || !content.trim()) {
      setStatus('Add a title and approved SOP content before publishing.')
      return
    }
    setPublishing(true)
    setStatus('Embedding the SOP. Larger documents take longer, so keep this tab open.')
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetchWithTimeout(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/ai/knowledge/ingest`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
          },
          credentials: 'include',
          body: JSON.stringify({ title: title.trim(), department, source: source.trim() || 'ENY internal SOP', content }),
        },
        API_TIMEOUTS.knowledgeIngest,
      )

      if (!response.ok) {
        setStatus(await describeHttpError(response, 'SOP publishing failed.'))
        return
      }

      const payload = await response.json().catch(() => null)
      if (!payload || typeof payload.chunks !== 'number') {
        setStatus('The SOP was sent but the response could not be read. Refresh the library to confirm it was published.')
        return
      }
      setStatus(`Published ${payload.chunks} knowledge chunk${payload.chunks === 1 ? '' : 's'} to ${department}.`)
      setContent('')
      setFileName(null)
    } catch (error) {
      setStatus(describeRequestFailure(error, 'SOP publishing failed.', API_TIMEOUTS.knowledgeIngest))
    } finally {
      setPublishing(false)
    }
  }

  return (
    <section className="overflow-hidden rounded-[24px] border border-slate-800 bg-slate-950 text-white shadow-[0_24px_60px_rgba(15,23,42,0.25)]">
      <div className="border-b border-slate-800 bg-[radial-gradient(circle_at_top_right,_rgba(56,189,248,0.16),_transparent_36%)] p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.24em] text-sky-300">Knowledge publishing</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Publish an SOP to ENY AI</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Approved Markdown and plain text are chunked, embedded, and made available only to the selected department.</p>
          </div>
          <FileText className="h-5 w-5 text-sky-300" />
        </div>
      </div>
      <div className="grid gap-5 p-6 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-4">
          <label className="block"><span className="mb-2 block text-xs font-medium text-slate-300">SOP title and version</span><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="ENY-SALES-LEAD-QUALIFICATION-v1" className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-600 focus:border-sky-400" /></label>
          <label className="block"><span className="mb-2 block text-xs font-medium text-slate-300">Department scope</span><select value={department} onChange={(event) => setDepartment(event.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-sky-400">{departments.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label className="block"><span className="mb-2 block text-xs font-medium text-slate-300">Source</span><input value={source} onChange={(event) => setSource(event.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-sky-400" /></label>
          <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-slate-700 bg-slate-900/60 p-4 hover:border-sky-400"><UploadCloud className="h-5 w-5 text-sky-300" /><span className="min-w-0"><span className="block text-sm font-medium text-slate-200">Load Markdown or text</span><span className="block truncate text-xs text-slate-500">{fileName || '.md and .txt supported'}</span></span><input type="file" accept=".md,.txt,text/markdown,text/plain" onChange={loadTextFile} className="sr-only" /></label>
          <button type="button" onClick={() => void publish()} disabled={publishing} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-sky-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-300 disabled:opacity-50">{publishing && <Loader2 className="h-4 w-4 animate-spin" />} {publishing ? 'Publishing...' : 'Publish SOP to AI knowledge'}</button>
          {status && <p className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs leading-5 text-slate-300">{status}</p>}
        </div>
        <label className="block"><span className="mb-2 block text-xs font-medium text-slate-300">Approved SOP content</span><textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder={'# Purpose\n\n## Procedure\n\n1. Review the lead.\n2. Confirm ownership.\n\n| Decision | Action |\n|---|---|\n| Hot | Contact immediately |'} className="min-h-[360px] w-full resize-y rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 font-mono text-xs leading-6 text-slate-200 outline-none placeholder:text-slate-600 focus:border-sky-400" /></label>
      </div>
    </section>
  )
}
