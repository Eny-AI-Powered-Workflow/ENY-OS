'use client'

import { ChangeEvent, useEffect, useState } from 'react'
import { FileText, Loader2, UploadCloud } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'
import { API_TIMEOUTS, describeHttpError, describeRequestFailure, fetchWithTimeout } from '@/lib/api'
import { departmentLabel } from '@/lib/knowledge'

export default function SOPPublisher() {
  const { can, permissions } = usePermissions()
  const [departments, setDepartments] = useState<string[]>([])
  const [departmentsLoading, setDepartmentsLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [department, setDepartment] = useState('enrollment')
  const [source, setSource] = useState('ENY internal SOP')
  const [content, setContent] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [publishing, setPublishing] = useState(false)

  useEffect(() => {
    if (!can('agents:configure')) return
    let active = true

    const loadDepartments = async () => {
      setDepartmentsLoading(true)
      try {
        const { data: { session } } = await supabase.auth.getSession()
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ai/knowledge/departments`, {
          headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
          credentials: 'include',
        })
        const payload = await response.json()
        if (!response.ok) {
          throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load departments')
        }
        if (!Array.isArray(payload.departments) || !payload.departments.every((value: unknown) => typeof value === 'string')) {
          throw new Error('The departments response was invalid')
        }
        if (!active) return
        setDepartments(payload.departments)
        if (payload.departments.length > 0) {
          setDepartment((current) => payload.departments.includes(current) ? current : payload.departments[0])
        }
        setStatus(payload.departments.length > 0 ? null : 'No departments are configured for SOP resources.')
      } catch (error) {
        if (active) {
          setStatus(error instanceof Error ? error.message : 'Unable to load departments')
        }
      } finally {
        if (active) setDepartmentsLoading(false)
      }
    }

    void loadDepartments()
    return () => {
      active = false
    }
  }, [permissions])

  if (!can('agents:configure')) return null

  const loadTextFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const extension = file.name.split('.').pop()?.toLowerCase()
    if (!extension || !['md', 'txt', 'pdf', 'docx', 'pptx'].includes(extension)) {
      setStatus('Supported files are Markdown, text, PDF, Word (.docx), and PowerPoint (.pptx).')
      event.target.value = ''
      return
    }
    if (extension === 'md' || extension === 'txt') {
      setContent(await file.text())
      setSelectedFile(null)
    } else {
      setContent('')
      setSelectedFile(file)
    }
    setFileName(file.name)
    if (!title) setTitle(file.name.replace(/\.(md|txt|pdf|docx|pptx)$/i, ''))
    setStatus(null)
  }

  const publish = async () => {
    if (!title.trim() || (!selectedFile && !content.trim())) {
      setStatus('Add a title and approved SOP content before publishing.')
      return
    }
    setPublishing(true)
    setStatus(selectedFile
      ? 'Extracting document text and embedding the SOP. Larger documents take longer, so keep this tab open.'
      : 'Embedding the SOP. Larger documents take longer, so keep this tab open.')
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const requestBody = selectedFile
        ? (() => {
            const formData = new FormData()
            formData.append('title', title.trim())
            formData.append('department', department)
            formData.append('source', source.trim() || 'ENY internal SOP')
            formData.append('file', selectedFile)
            return formData
          })()
        : JSON.stringify({ title: title.trim(), department, source: source.trim() || 'ENY internal SOP', content })
      const response = await fetchWithTimeout(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/ai/knowledge/${selectedFile ? 'upload' : 'ingest'}`,
        {
          method: 'POST',
          headers: {
            ...(!selectedFile ? { 'Content-Type': 'application/json' } : {}),
            ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
          },
          credentials: 'include',
          body: requestBody,
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
      setSelectedFile(null)
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
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Markdown, text, searchable PDFs, Word documents, and PowerPoint presentations are extracted, embedded, and made available only to the selected department.</p>
          </div>
          <FileText className="h-5 w-5 text-sky-300" />
        </div>
      </div>
      <div className="grid gap-5 p-6 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-4">
          <label className="block"><span className="mb-2 block text-xs font-medium text-slate-300">SOP title and version</span><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="ENY-SALES-LEAD-QUALIFICATION-v1" className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-600 focus:border-sky-400" /></label>
          <label className="block"><span className="mb-2 block text-xs font-medium text-slate-300">Department scope</span><select value={department} onChange={(event) => setDepartment(event.target.value)} disabled={departmentsLoading || departments.length === 0} className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-sky-400 disabled:cursor-not-allowed disabled:opacity-60">{departmentsLoading ? <option value="">Loading departments...</option> : departments.map((value) => <option key={value} value={value}>{departmentLabel(value)}</option>)}</select></label>
          <label className="block"><span className="mb-2 block text-xs font-medium text-slate-300">Source</span><input value={source} onChange={(event) => setSource(event.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-sky-400" /></label>
          <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-slate-700 bg-slate-900/60 p-4 hover:border-sky-400"><UploadCloud className="h-5 w-5 text-sky-300" /><span className="min-w-0"><span className="block text-sm font-medium text-slate-200">Load an SOP document</span><span className="block truncate text-xs text-slate-500">{fileName || '.md, .txt, .pdf, .docx, and .pptx supported'}</span></span><input type="file" accept=".md,.txt,.pdf,.docx,.pptx,text/markdown,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation" onChange={loadTextFile} className="sr-only" /></label>
          <button type="button" onClick={() => void publish()} disabled={publishing || departmentsLoading || departments.length === 0} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-sky-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-300 disabled:opacity-50">{publishing && <Loader2 className="h-4 w-4 animate-spin" />} {publishing ? 'Publishing...' : 'Publish SOP to AI knowledge'}</button>
          {status && <p className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs leading-5 text-slate-300">{status}</p>}
        </div>
        <label className="block"><span className="mb-2 block text-xs font-medium text-slate-300">Approved SOP content</span><textarea value={content} onChange={(event) => setContent(event.target.value)} disabled={Boolean(selectedFile)} placeholder={selectedFile ? 'Document text is extracted securely when you publish.' : '# Purpose\n\n## Procedure\n\n1. Review the lead.\n2. Confirm ownership.\n\n| Decision | Action |\n|---|---|\n| Hot | Contact immediately |'} className="min-h-[360px] w-full resize-y rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 font-mono text-xs leading-6 text-slate-200 outline-none placeholder:text-slate-600 focus:border-sky-400 disabled:cursor-not-allowed disabled:opacity-70" /></label>
      </div>
    </section>
  )
}
