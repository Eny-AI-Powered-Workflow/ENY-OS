'use client'

import { ChangeEvent, FormEvent, useEffect, useState } from 'react'
import { Clapperboard, FileVideo2, Loader2, RefreshCw, Sparkles, Upload } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'

type VideoAsset = {
  id: string
  title: string
  original_filename: string
  mime_type: string
  size_bytes: number
  status: string
  transcript: string | null
  transcript_provider: string | null
  generated_outputs: Array<{ kind: string; title: string; start_seconds?: number; end_seconds?: number }>
  created_at: string | null
}

export default function MarketingVideoWorkspace() {
  const [assets, setAssets] = useState<VideoAsset[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(true)
  const [workingId, setWorkingId] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [whisperReady, setWhisperReady] = useState(false)
  const [canvaReady, setCanvaReady] = useState(false)

  const headers = async (): Promise<HeadersInit> => {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}
  }

  const load = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/video/assets`, { headers: await headers(), credentials: 'include' })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load video assets')
      setAssets(payload.assets || [])
      setWhisperReady(Boolean(payload.providers?.whisper?.configured))
      setCanvaReady(Boolean(payload.providers?.canva?.configured))
      setMessage(null)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load video assets')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] || null
    setFile(selected)
    if (selected && !title) setTitle(selected.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '))
  }

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file || !title.trim()) return
    setWorkingId('upload')
    setMessage('Uploading source media to private Marketing storage...')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('title', title.trim())
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/video/assets`, { method: 'POST', headers: await headers(), credentials: 'include', body: form })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Video upload failed')
      setMessage('Source media stored privately. Transcribe it to build the review pack.')
      setFile(null)
      setTitle('')
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Video upload failed')
    } finally {
      setWorkingId(null)
    }
  }

  const runAction = async (asset: VideoAsset, action: 'transcribe' | 'generate-pack') => {
    setWorkingId(asset.id)
    setMessage(action === 'transcribe' ? 'Transcribing source media with Whisper...' : 'Generating a reviewable content pack...')
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/video/assets/${asset.id}/${action}`, { method: 'POST', headers: await headers(), credentials: 'include' })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Video processing failed')
      const transcriptStatus = payload.transcription?.status
      setMessage(transcriptStatus && transcriptStatus !== 'transcribed' ? payload.transcription.message : action === 'transcribe' ? 'Transcript saved with provider timestamps.' : `Generated ${payload.draft_count} drafts. They remain in Draft until approved.`)
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Video processing failed')
    } finally {
      setWorkingId(null)
    }
  }

  const fileSize = (bytes: number) => `${(bytes / (1024 * 1024)).toFixed(1)} MB`

  return (
    <section className="space-y-5 rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-[10px] uppercase tracking-[0.22em] text-rose-700">ENY-MKT-VIDEO</p><h2 className="mt-1 text-2xl font-semibold text-slate-950">Video repurposing</h2><p className="mt-2 text-sm text-slate-500">Private source media becomes timestamped drafts for human review.</p></div>
        <button type="button" onClick={() => void load()} title="Refresh video assets" className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </div>
      <form onSubmit={upload} className="grid gap-3 rounded-xl border border-rose-100 bg-rose-50/70 p-4 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
        <label className="block"><span className="mb-2 block text-xs font-semibold text-slate-700">Source title</span><input value={title} onChange={(event) => setTitle(event.target.value)} required minLength={3} maxLength={240} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-rose-500" /></label>
        <label className="block"><span className="mb-2 block text-xs font-semibold text-slate-700">Video or audio file</span><input type="file" accept="video/mp4,video/webm,video/quicktime,audio/*" onChange={onFileChange} required className="block w-full text-xs text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-white file:px-3 file:py-2 file:text-xs file:font-semibold file:text-slate-700" /></label>
        <button type="submit" disabled={!file || workingId === 'upload'} className="inline-flex items-center justify-center gap-2 rounded-lg bg-rose-800 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-900 disabled:opacity-50">{workingId === 'upload' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}Upload source</button>
      </form>
      <div className="flex flex-wrap gap-4 border-b border-slate-100 pb-3 text-xs text-slate-500"><span>Whisper: {whisperReady ? 'configured' : 'not configured'}</span><span>Canva: {canvaReady ? 'configured' : 'not configured'}</span><span>Canva access is optional and backend-only.</span></div>
      {message && <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{message}</p>}
      <div className="space-y-3">
        {assets.map((asset) => <article key={asset.id} className="rounded-xl border border-slate-200 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3"><div className="flex items-start gap-3"><FileVideo2 className="mt-0.5 h-4 w-4 text-rose-700" /><div><h3 className="font-semibold text-slate-900">{asset.title}</h3><p className="mt-1 text-xs text-slate-500">{asset.original_filename} · {fileSize(asset.size_bytes)} · {asset.status.replaceAll('_', ' ')}</p></div></div><div className="flex flex-wrap gap-2">{!asset.transcript && <button type="button" disabled={Boolean(workingId)} onClick={() => void runAction(asset, 'transcribe')} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-50"><Clapperboard className="h-3.5 w-3.5" />Transcribe</button>}{asset.transcript && <button type="button" disabled={Boolean(workingId)} onClick={() => void runAction(asset, 'generate-pack')} className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"><Sparkles className="h-3.5 w-3.5" />Generate review pack</button>}</div></div>
          {asset.transcript && <details className="mt-3"><summary className="cursor-pointer text-xs font-semibold text-slate-700">Transcript · {asset.transcript_provider || 'provider unknown'}</summary><p className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-600">{asset.transcript}</p></details>}
          {asset.generated_outputs.length > 0 && <div className="mt-3 grid gap-2 sm:grid-cols-2">{asset.generated_outputs.map((output, index) => <div key={`${output.kind}-${index}`} className="rounded-lg bg-slate-50 p-3 text-xs"><p className="font-semibold text-slate-800">{output.kind.replaceAll('_', ' ')} · {output.title}</p>{typeof output.start_seconds === 'number' && <p className="mt-1 text-slate-500">{output.start_seconds.toFixed(1)}s–{(output.end_seconds || 0).toFixed(1)}s</p>}<p className="mt-1 text-slate-500">Saved as approval-required draft content.</p></div>)}</div>}
        </article>)}
        {!assets.length && !loading && <p className="py-6 text-center text-sm text-slate-500">No source recordings have been uploaded.</p>}
      </div>
    </section>
  )
}
