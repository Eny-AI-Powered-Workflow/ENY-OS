'use client'

import { ChangeEvent, FormEvent, useEffect, useState } from 'react'
import { Check, Clapperboard, FileVideo2, Loader2, RefreshCw, Sparkles, Upload, Video, X } from 'lucide-react'
import { usePermissions } from '@/lib/permissions'
import { supabase } from '@/lib/supabaseClient'

type VideoOutput = {
  kind?: string
  title: string
  start_seconds: number
  end_seconds: number
  rationale?: string
  caption?: string
  hook?: string
  status: 'draft' | 'approved' | 'rejected' | 'published'
  review_note?: string
  published_url?: string | null
  canva?: { job_id: string; status: string; url?: string; edit_url?: string; view_url?: string }
}

type VideoAsset = {
  id: string
  title: string
  original_filename: string
  mime_type: string
  size_bytes: number
  status: string
  team: string
  audience: string
  transcript: string | null
  transcript_provider: string | null
  generated_outputs: VideoOutput[]
  created_at: string | null
}

type ApiPayload = {
  detail?: string
  assets?: VideoAsset[]
  authorization_url?: string
  connected?: boolean
  configured?: boolean
  status?: string
  [key: string]: unknown
}

const apiBase = process.env.NEXT_PUBLIC_API_URL

export default function VideographerWorkspace() {
  const { permissions } = usePermissions()
  const canRead = permissions.includes('video:read')
  const canUpload = permissions.includes('video:upload')
  const canEdit = permissions.includes('video:edit')
  const canApprove = permissions.includes('video:approve')
  const canPublish = permissions.includes('video:publish')
  const canUseCanva = permissions.includes('design:canva')
  const [assets, setAssets] = useState<VideoAsset[]>([])
  const [teamFilter, setTeamFilter] = useState('')
  const [audienceFilter, setAudienceFilter] = useState('')
  const [ownerFilter, setOwnerFilter] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [team, setTeam] = useState('videographer')
  const [audience, setAudience] = useState('marketing')
  const [channel, setChannel] = useState('instagram')
  const [canvaTemplateId, setCanvaTemplateId] = useState('')
  const [canvaData, setCanvaData] = useState('{\n  "title": "{{title}}",\n  "caption": "{{caption}}",\n  "hook": "{{hook}}"\n}')
  const [reviewNote, setReviewNote] = useState('Reviewed for accuracy and brand alignment.')
  const [canvaConnected, setCanvaConnected] = useState(false)
  const [canvaConfigured, setCanvaConfigured] = useState(false)
  const [loading, setLoading] = useState(true)
  const [workingId, setWorkingId] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const headers = async (json = false): Promise<HeadersInit> => {
    const { data: { session } } = await supabase.auth.getSession()
    return {
      ...(json ? { 'Content-Type': 'application/json' } : {}),
      ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
    }
  }

  const request = async (path: string, init: RequestInit = {}): Promise<ApiPayload> => {
    const response = await fetch(`${apiBase}/api/v1${path}`, { ...init, credentials: 'include' })
    const payload = await response.json().catch(() => ({})) as ApiPayload
    if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : `Request failed (HTTP ${response.status})`)
    return payload
  }

  const load = async () => {
    if (!canRead) return
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (teamFilter) params.set('team', teamFilter)
      if (audienceFilter) params.set('audience', audienceFilter)
      if (ownerFilter.trim()) params.set('owner_id', ownerFilter.trim())
      const suffix = params.size ? `?${params.toString()}` : ''
      const payload = await request(`/videographer/assets${suffix}`, { headers: await headers() })
      setAssets(payload.assets || [])
      if (canUseCanva) {
        try {
          const canva = await request('/videographer/canva/status', { headers: await headers() })
          setCanvaConfigured(Boolean(canva.configured))
          setCanvaConnected(Boolean(canva.connected))
        } catch {
          setCanvaConnected(false)
        }
      }
      setMessage(null)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load video assets')
    } finally {
      setLoading(false)
    }
  }

  const permissionKey = permissions.join('|')
  useEffect(() => { void load() }, [permissionKey, teamFilter, audienceFilter, ownerFilter])

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] || null
    setFile(selected)
    if (selected && !title) setTitle(selected.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '))
  }

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file || !title.trim()) return
    setWorkingId('upload')
    setMessage('Uploading source media to private storage...')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('title', title.trim())
      form.append('team', team)
      form.append('audience', audience)
      await request('/videographer/assets', { method: 'POST', headers: await headers(), body: form })
      setFile(null)
      setTitle('')
      setMessage('Source recording stored privately.')
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Video upload failed')
    } finally {
      setWorkingId(null)
    }
  }

  const runAction = async (asset: VideoAsset, action: 'transcribe' | 'generate-clips') => {
    setWorkingId(asset.id)
    setMessage(action === 'transcribe' ? 'Transcribing source media with Whisper...' : 'Generating timestamped clip and caption drafts...')
    try {
      const result = await request(`/videographer/assets/${asset.id}/${action}`, {
        method: 'POST', headers: await headers(),
      })
      const transcription = result.transcription as { status?: string; message?: string } | undefined
      setMessage(transcription && transcription.status !== 'transcribed'
        ? transcription.message || 'Transcription is not configured.'
        : action === 'transcribe' ? 'Transcript and timestamps saved.' : 'Clip and caption drafts are ready for review.')
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Video processing failed')
    } finally {
      setWorkingId(null)
    }
  }

  const reviewOutput = async (asset: VideoAsset, outputIndex: number, decision: 'approved' | 'rejected') => {
    if (reviewNote.trim().length < 3) {
      setMessage('Enter a review note before approving or rejecting a clip.')
      return
    }
    setWorkingId(`${asset.id}-${outputIndex}`)
    try {
      await request(`/videographer/assets/${asset.id}/outputs/${outputIndex}/review`, {
        method: 'POST', headers: await headers(true),
        body: JSON.stringify({ decision, note: reviewNote.trim() }),
      })
      setMessage(decision === 'approved' ? 'Clip approved for publishing.' : 'Clip returned as rejected.')
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Clip review failed')
    } finally {
      setWorkingId(null)
    }
  }

  const createCanvaDesign = async (asset: VideoAsset, output: VideoOutput, outputIndex: number) => {
    if (!canvaTemplateId.trim()) {
      setMessage('Enter a Canva Brand Template ID first.')
      return
    }
    try {
      const values = JSON.parse(canvaData) as Record<string, unknown>
      const data = Object.fromEntries(Object.entries(values).map(([key, value]) => [
        key,
        typeof value === 'string'
          ? value.replaceAll('{{title}}', output.title).replaceAll('{{caption}}', output.caption || '').replaceAll('{{hook}}', output.hook || '')
          : value,
      ]))
      setWorkingId(`${asset.id}-${outputIndex}`)
      const result = await request(`/videographer/assets/${asset.id}/outputs/${outputIndex}/canva`, {
        method: 'POST', headers: await headers(true),
        body: JSON.stringify({ brand_template_id: canvaTemplateId.trim(), data }),
      })
      const job = result.canva_job as { status?: string } | undefined
      setMessage(`Canva Autofill started${job?.status ? ` (${job.status})` : ''}.`)
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Canva design generation failed. Check the template data JSON.')
    } finally {
      setWorkingId(null)
    }
  }

  const connectCanva = async () => {
    try {
      const result = await request('/designer/canva/connect', { method: 'POST', headers: await headers() })
      if (typeof result.authorization_url === 'string') window.location.assign(result.authorization_url)
      else setMessage('Canva did not return an authorization link.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not connect Canva')
    }
  }

  const pollCanvaDesign = async (asset: VideoAsset, outputIndex: number) => {
    setWorkingId(`${asset.id}-${outputIndex}`)
    try {
      const result = await request(`/videographer/assets/${asset.id}/outputs/${outputIndex}/canva/poll`, {
        method: 'POST', headers: await headers(),
      })
      const job = result.canva_job as { status?: string } | undefined
      setMessage(`Canva Autofill status: ${job?.status || 'unknown'}.`)
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to check Canva Autofill status')
    } finally {
      setWorkingId(null)
    }
  }

  const publish = async (asset: VideoAsset, outputIndex: number) => {
    setWorkingId(`${asset.id}-${outputIndex}`)
    try {
      const result = await request(`/videographer/assets/${asset.id}/outputs/${outputIndex}/publish?channel=${encodeURIComponent(channel)}`, {
        method: 'POST', headers: await headers(),
      })
      const clip = result.clip as VideoOutput | undefined
      setMessage(clip?.published_url ? `Published to ${channel}: ${clip.published_url}` : `n8n confirmed publication to ${channel}.`)
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Publishing failed or was not confirmed by n8n')
    } finally {
      setWorkingId(null)
    }
  }

  const fileSize = (bytes: number) => `${(bytes / (1024 * 1024)).toFixed(1)} MB`

  if (!canRead) {
    return <section className="border-l-4 border-rose-500 bg-slate-900 px-5 py-4 text-sm text-slate-200">Your account does not have access to Videographer assets.</section>
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-teal-300">Production · Review · Distribution</p>
          <h1 className="mt-1 text-3xl font-semibold text-white">Videographer</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">Manage source recordings, transcript-based clips, approvals, and channel handoff.</p>
        </div>
        <button type="button" onClick={() => void load()} title="Refresh video assets" className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </header>

      {message && <p role="status" className="border-l-4 border-teal-400 bg-slate-900 px-4 py-3 text-sm text-slate-200">{message}</p>}

      {canUpload && <form onSubmit={upload} className="grid gap-3 border-b border-slate-800 pb-5 lg:grid-cols-[1fr_1fr_150px_150px_auto] lg:items-end">
        <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Asset title</span><input value={title} onChange={(event) => setTitle(event.target.value)} required minLength={3} maxLength={240} className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-teal-400" /></label>
        <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Video or audio file</span><input type="file" accept="video/mp4,video/webm,video/quicktime,audio/*" onChange={onFileChange} required className="block w-full text-xs text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-slate-700 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-white" /></label>
        <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Team</span><input value={team} onChange={(event) => setTeam(event.target.value)} required maxLength={80} className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" /></label>
        <label className="block"><span className="mb-1.5 block text-xs font-medium text-slate-300">Audience</span><select value={audience} onChange={(event) => setAudience(event.target.value)} className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white">{['marketing', 'programs', 'shared', 'student_success'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select></label>
        <button type="submit" disabled={!file || workingId === 'upload'} className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50">{workingId === 'upload' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}Upload</button>
      </form>}

      <div className="flex flex-wrap items-end gap-3 border-b border-slate-800 pb-4">
        <label className="block"><span className="mb-1 block text-[11px] text-slate-400">Team filter</span><select value={teamFilter} onChange={(event) => setTeamFilter(event.target.value)} className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white"><option value="">All teams</option><option value="videographer">Videographer</option><option value="marketing">Marketing</option></select></label>
        <label className="block"><span className="mb-1 block text-[11px] text-slate-400">Audience filter</span><select value={audienceFilter} onChange={(event) => setAudienceFilter(event.target.value)} className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white"><option value="">All audiences</option>{['marketing', 'programs', 'shared', 'student_success'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select></label>
        <label className="block min-w-56"><span className="mb-1 block text-[11px] text-slate-400">Owner ID</span><input value={ownerFilter} onChange={(event) => setOwnerFilter(event.target.value)} placeholder="Optional user UUID" className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-500" /></label>
        {canUseCanva && <div className="ml-auto flex items-center gap-2 text-xs text-slate-300"><span>Canva {canvaConnected ? 'connected' : canvaConfigured ? 'ready to connect' : 'not configured'}</span>{!canvaConnected && canvaConfigured && <button type="button" onClick={() => void connectCanva()} className="rounded-md border border-slate-600 px-2.5 py-1.5 hover:bg-slate-800">Connect</button>}</div>}
      </div>

      {canUseCanva && <details className="border-b border-slate-800 pb-4">
        <summary className="cursor-pointer text-xs font-semibold text-slate-300">Canva template mapping</summary>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_2fr]">
          <label><span className="mb-1 block text-[11px] text-slate-400">Brand Template ID</span><input value={canvaTemplateId} onChange={(event) => setCanvaTemplateId(event.target.value)} className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white" /></label>
          <label><span className="mb-1 block text-[11px] text-slate-400">Autofill data JSON (supports {'{{title}}'}, {'{{caption}}'}, {'{{hook}}'})</span><textarea rows={3} value={canvaData} onChange={(event) => setCanvaData(event.target.value)} className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-white" /></label>
        </div>
      </details>}

      <section className="space-y-4">
        <div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-white">Video assets <span className="ml-1 text-slate-400">{assets.length}</span></h2>{loading && <span className="text-xs text-slate-400">Loading...</span>}</div>
        {assets.map((asset) => <article key={asset.id} className="border-t border-slate-800 pt-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3"><FileVideo2 className="mt-1 h-4 w-4 shrink-0 text-teal-300" /><div className="min-w-0"><h3 className="truncate text-sm font-semibold text-white">{asset.title}</h3><p className="mt-1 text-xs text-slate-400">{asset.original_filename} · {fileSize(asset.size_bytes)} · {asset.team} · {asset.audience} · {asset.status.replaceAll('_', ' ')}</p></div></div>
            <div className="flex flex-wrap gap-2">
              {canEdit && !asset.transcript && <button type="button" disabled={Boolean(workingId)} onClick={() => void runAction(asset, 'transcribe')} className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 disabled:opacity-50"><Clapperboard className="h-3.5 w-3.5" />Transcribe</button>}
              {canEdit && asset.transcript && <button type="button" disabled={Boolean(workingId)} onClick={() => void runAction(asset, 'generate-clips')} className="inline-flex items-center gap-1.5 rounded-md bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"><Sparkles className="h-3.5 w-3.5" />Generate clips</button>}
            </div>
          </div>
          {asset.transcript && <details className="mt-3"><summary className="cursor-pointer text-xs font-semibold text-slate-300">Transcript · {asset.transcript_provider || 'provider unknown'}</summary><p className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap border-l border-slate-700 pl-3 text-xs leading-5 text-slate-400">{asset.transcript}</p></details>}
          {asset.generated_outputs?.length > 0 && <div className="mt-4 space-y-3">{asset.generated_outputs.map((output, outputIndex) => {
            const isWorking = workingId === `${asset.id}-${outputIndex}`
            return <div key={`${output.title}-${outputIndex}`} className="border-l-2 border-slate-700 pl-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h4 className="text-sm font-semibold text-slate-100">{output.title}</h4><span className="rounded-sm bg-slate-800 px-2 py-0.5 text-[10px] uppercase text-slate-300">{output.status}</span></div><p className="mt-1 text-xs text-slate-400">{output.start_seconds.toFixed(1)}s–{output.end_seconds.toFixed(1)}s{output.rationale ? ` · ${output.rationale}` : ''}</p></div>
                <div className="flex flex-wrap gap-2">
                  {canApprove && output.status === 'draft' && <><button type="button" disabled={Boolean(workingId)} onClick={() => void reviewOutput(asset, outputIndex, 'approved')} title="Approve clip" className="flex h-8 w-8 items-center justify-center rounded-md border border-emerald-700 text-emerald-300 hover:bg-emerald-950 disabled:opacity-50"><Check className="h-4 w-4" /></button><button type="button" disabled={Boolean(workingId)} onClick={() => void reviewOutput(asset, outputIndex, 'rejected')} title="Reject clip" className="flex h-8 w-8 items-center justify-center rounded-md border border-rose-800 text-rose-300 hover:bg-rose-950 disabled:opacity-50"><X className="h-4 w-4" /></button></>}
                  {canUseCanva && canEdit && output.status === 'approved' && <button type="button" disabled={Boolean(workingId) || !canvaConnected} onClick={() => void (output.canva ? pollCanvaDesign(asset, outputIndex) : createCanvaDesign(asset, output, outputIndex))} className="rounded-md border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 disabled:opacity-50">{isWorking ? 'Working...' : output.canva ? `Check Canva · ${output.canva.status}` : 'Create Canva design'}</button>}
                  {canPublish && output.status === 'approved' && <><select aria-label={`Publish ${output.title} to`} value={channel} onChange={(event) => setChannel(event.target.value)} className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-white">{['instagram', 'facebook', 'linkedin', 'tiktok', 'youtube'].map((value) => <option key={value} value={value}>{value}</option>)}</select><button type="button" disabled={Boolean(workingId)} onClick={() => void publish(asset, outputIndex)} className="inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-900 disabled:opacity-50">{isWorking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Video className="h-3.5 w-3.5" />}Publish</button></>}
                </div>
              </div>
              {output.hook && <p className="mt-2 text-xs text-teal-200">{output.hook}</p>}
              {output.caption && <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-300">{output.caption}</p>}
              {output.review_note && <p className="mt-2 text-[11px] text-slate-500">Review: {output.review_note}</p>}
              {output.canva?.edit_url && <a href={output.canva.edit_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-teal-300 underline">Open Canva design</a>}
              {output.published_url && <a href={output.published_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-teal-300 underline">View published asset</a>}
            </div>
          })}</div>}
        </article>)}
        {!assets.length && !loading && <div className="flex items-center gap-3 border-t border-slate-800 py-8 text-sm text-slate-400"><Video className="h-5 w-5" />No video assets match these filters.</div>}
      </section>

      {canApprove && <div className="border-t border-slate-800 pt-4"><label className="block max-w-2xl"><span className="mb-1 block text-xs text-slate-400">Approval or rejection note</span><input value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} minLength={3} maxLength={1000} className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white" /></label></div>}
    </div>
  )
}