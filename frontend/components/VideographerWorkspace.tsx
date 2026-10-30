'use client'

import { ChangeEvent, DragEvent as ReactDragEvent, FormEvent, useEffect, useRef, useState } from 'react'
import { Activity, Check, CheckCircle2, Clapperboard, CloudUpload, FileVideo2, HardDrive, Loader2, RefreshCw, Search, SlidersHorizontal, Sparkles, Upload, Video, X } from 'lucide-react'
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
  const [searchTerm, setSearchTerm] = useState('')
  const [assetFilter, setAssetFilter] = useState<'all' | 'marketing' | 'raw' | 'pending' | 'approved'>('all')
  const [file, setFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
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
      let canvaStatusError: string | null = null
      if (canUseCanva) {
        try {
          const canva = await request('/canva/status', { headers: await headers() })
          setCanvaConfigured(Boolean(canva.configured))
          setCanvaConnected(Boolean(canva.connected))
        } catch (error) {
          setCanvaConnected(false)
          canvaStatusError = error instanceof Error
            ? `Unable to verify Canva connection: ${error.message}`
            : 'Unable to verify Canva connection.'
        }
      }
      setMessage(canvaStatusError)
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

  const onFileDrop = (event: ReactDragEvent<HTMLLabelElement>) => {
    event.preventDefault()
    const selected = event.dataTransfer.files[0]
    if (!selected) return
    setFile(selected)
    if (!title) setTitle(selected.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '))
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
      if (fileInputRef.current) fileInputRef.current.value = ''
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
    const popup = window.open(
      'about:blank',
      'eny-canva-oauth',
      'popup,width=640,height=800',
    )
    if (!popup) {
      setMessage('Your browser blocked the Canva sign-in window. Allow pop-ups for this site and try again.')
      return
    }

    let finished = false
    const channel = typeof BroadcastChannel === 'undefined'
      ? null
      : new BroadcastChannel('eny-canva-oauth')
    const cleanup = () => {
      if (finished) return
      finished = true
      window.removeEventListener('message', handleMessage)
      if (channel) channel.close()
      window.clearInterval(closePoll)
      window.clearTimeout(timeout)
    }
    const complete = (status: unknown) => {
      if (finished) return
      cleanup()
      popup.close()
      if (status !== 'connected') {
        setMessage('Canva authorization did not complete. Close the sign-in window and try again.')
        return
      }

      void (async () => {
        try {
          const status = await request('/canva/status', { headers: await headers() })
          setCanvaConfigured(Boolean(status.configured))
          setCanvaConnected(Boolean(status.connected))
          setMessage(status.connected
            ? 'Shared Canva account connected.'
            : 'Canva authorization finished, but the backend has not confirmed a connection. Refresh and check the backend logs.')
        } catch (error) {
          setCanvaConnected(false)
          setMessage(error instanceof Error
            ? `Canva authorization finished, but connection status could not be checked: ${error.message}`
            : 'Canva authorization finished, but connection status could not be checked.')
        }
      })()
    }
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.source !== popup) return
      if (!event.data || event.data.type !== 'eny-canva-oauth-complete') return
      complete(event.data.status)
    }
    if (channel) {
      channel.onmessage = (event: MessageEvent) => {
        if (event.data?.type === 'eny-canva-oauth-complete') complete(event.data.status)
      }
    }
    const closePoll = window.setInterval(() => {
      if (popup.closed) {
        cleanup()
        setMessage('Canva sign-in window was closed before authorization completed.')
      }
    }, 500)
    const timeout = window.setTimeout(() => {
      cleanup()
      if (!popup.closed) {
        popup.close()
        setMessage('Canva sign-in timed out. Try connecting again.')
      }
    }, 10 * 60 * 1000)
    window.addEventListener('message', handleMessage)

    try {
      const result = await request('/canva/connect', { method: 'POST', headers: await headers() })
      if (typeof result.authorization_url !== 'string') {
        throw new Error('Canva did not return an authorization link.')
      }
      setMessage('Complete Canva authorization in the sign-in window.')
      popup.location.assign(result.authorization_url)
    } catch (error) {
      cleanup()
      popup.close()
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
  const totalStorage = assets.reduce((total, asset) => total + asset.size_bytes, 0)
  const transcribedCount = assets.filter((asset) => Boolean(asset.transcript)).length
  const visibleAssets = assets.filter((asset) => {
    const query = searchTerm.trim().toLowerCase()
    const matchesSearch = !query || [
      asset.title,
      asset.original_filename,
      asset.team,
      asset.audience,
      asset.status,
    ].some((value) => value.toLowerCase().includes(query))
    const status = asset.status.toLowerCase().replaceAll(' ', '_')
    const isPending = !asset.transcript && (
      status.includes('pending') || status.includes('queue') || status.includes('processing')
    )
    const matchesFilter = assetFilter === 'all'
      || (assetFilter === 'marketing' && asset.audience.toLowerCase() === 'marketing')
      || (assetFilter === 'raw' && !asset.transcript && !isPending)
      || (assetFilter === 'pending' && isPending)
      || (assetFilter === 'approved' && asset.generated_outputs?.some((output) => output.status === 'approved' || output.status === 'published'))
    return matchesSearch && matchesFilter
  })

  if (!canRead) {
    return <section className="rounded-2xl border border-rose-900/70 bg-[#171b26] px-5 py-4 text-sm text-rose-100">Your account does not have access to Videographer assets.</section>
  }

  return (
    <div className="relative -mx-4 -my-6 min-h-full overflow-hidden bg-[#0f131d] px-4 pb-10 pt-5 text-[#dfe2f1] sm:-mx-6 sm:px-6 sm:pt-6 lg:-mx-8 lg:px-8">
      <div className="pointer-events-none absolute -top-32 left-1/2 h-72 w-[36rem] -translate-x-1/2 rounded-full bg-cyan-400/[0.07] blur-3xl" />
      <div className="relative mx-auto max-w-[1440px] space-y-5">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-[#262a35] text-cyan-300">
              <Video className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">CineOps <span className="text-slate-600">/</span> Assets</p>
              <p className="text-sm font-semibold tracking-tight text-[#dfe2f1]">Videographer Hub</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {canUseCanva && <div className="flex items-center gap-2 rounded-full border border-white/5 bg-[#171b26] px-3 py-1.5 text-[11px] text-slate-300">
              <span className={`h-1.5 w-1.5 rounded-full ${canvaConnected ? 'bg-emerald-400' : 'bg-slate-500'}`} />
              Canva {canvaConnected ? 'Connected' : canvaConfigured ? 'Ready to connect' : 'Not configured'}
              {!canvaConnected && canvaConfigured && <button type="button" onClick={() => void connectCanva()} className="ml-1 font-semibold text-cyan-300 hover:text-cyan-200">Connect</button>}
            </div>}
            <button type="button" onClick={() => void load()} title="Refresh video assets" aria-label="Refresh video assets" className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#1c1f2a] text-slate-300 transition hover:bg-[#262a35] hover:text-cyan-300">
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </header>

        <section className="space-y-3">
          <div>
            <p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.19em] text-cyan-300">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-300" />
              Production · Review · Distribution
            </p>
            <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight text-[#dfe2f1] sm:text-[28px]">Videographer Hub</h1>
                <p className="mt-1 max-w-2xl text-xs leading-5 text-[#9ba7b6] sm:text-sm">Manage source telemetry, automated speech-to-cut tracks, and multi-channel sign-offs.</p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <div className="flex min-h-[72px] flex-col justify-between rounded-xl bg-[#171b26] p-3">
              <span className="text-[11px] text-slate-400">Active Queue</span>
              <span className="text-lg font-semibold text-cyan-300">{assets.length} {assets.length === 1 ? 'Clip' : 'Clips'}</span>
            </div>
            <div className="flex min-h-[72px] flex-col justify-between rounded-xl bg-[#171b26] p-3">
              <span className="flex items-center gap-1.5 text-[11px] text-slate-400"><HardDrive className="h-3 w-3" />Storage sync</span>
              <span className="text-lg font-semibold text-emerald-300">{fileSize(totalStorage)}</span>
            </div>
            <div className="flex min-h-[72px] flex-col justify-between rounded-xl bg-[#171b26] p-3">
              <span className="flex items-center gap-1.5 text-[11px] text-slate-400"><Activity className="h-3 w-3" />AI Pipeline</span>
              <span className="text-lg font-semibold text-indigo-200">{loading ? 'Syncing' : `${transcribedCount} Ready`}</span>
            </div>
          </div>
        </section>

        {message && <p role="status" className="rounded-xl border border-cyan-900/70 bg-[#111b25] px-4 py-3 text-sm text-cyan-100">{message}</p>}

        {canUpload && <form onSubmit={upload} className="space-y-3 rounded-2xl border border-white/[0.04] bg-[#1c1f2a] p-4 shadow-[0_12px_36px_rgba(2,6,23,0.28)] sm:p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-base font-semibold text-[#dfe2f1]"><CloudUpload className="h-5 w-5 text-cyan-300" />Ingest Footage</h2>
            <span className="text-[10px] text-slate-400 sm:text-xs">ProRes / MP4 / MOV</span>
          </div>
          <label className="block space-y-1.5">
            <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">Asset title</span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. GIS_Raw_Demo_v02.mp4" required minLength={3} maxLength={240} className="h-11 w-full rounded-lg border border-white/[0.04] bg-[#0a0e18] px-3 text-sm text-[#dfe2f1] outline-none placeholder:text-slate-500 focus:border-cyan-400/60" />
          </label>
          <label onDragOver={(event) => event.preventDefault()} onDrop={onFileDrop} className="relative flex min-h-32 cursor-pointer flex-col items-center justify-center overflow-hidden rounded-xl border border-dashed border-slate-700 bg-[#0a0e18] px-4 py-5 text-center transition hover:border-cyan-400/70 hover:bg-cyan-400/[0.03]">
            <input ref={fileInputRef} type="file" accept="video/mp4,video/webm,video/quicktime,audio/*" onChange={onFileChange} required aria-label="Choose source footage" className="absolute inset-0 h-full w-full cursor-pointer opacity-0" />
            <span className="mb-2 flex h-11 w-11 items-center justify-center rounded-full bg-cyan-400/10 text-cyan-300"><FileVideo2 className="h-6 w-6" /></span>
            <span className="text-sm font-semibold text-[#dfe2f1]">{file ? file.name : 'Tap or drag source footage'}</span>
            <span className="mt-1 text-xs text-slate-400">{file ? `${fileSize(file.size)} · ${file.type || 'Media file'}` : 'High-bitrate files auto-encode to proxy'}</span>
            <span className="mt-3 flex flex-wrap justify-center gap-1.5 text-[10px] text-slate-400"><span className="rounded-full bg-[#262a35] px-2 py-0.5">4K DCI</span><span className="rounded-full bg-[#262a35] px-2 py-0.5">.MP4</span><span className="rounded-full bg-[#262a35] px-2 py-0.5">.MOV</span><span className="rounded-full bg-[#262a35] px-2 py-0.5">H.265</span></span>
          </label>
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="flex min-h-14 items-center justify-between gap-3 rounded-lg bg-[#0a0e18] px-3 py-2">
              <span className="min-w-0"><span className="block text-[10px] text-slate-400">Assigned Unit</span><span className="mt-1 flex items-center gap-1.5 text-xs text-[#dfe2f1]"><span className="h-1.5 w-1.5 rounded-full bg-cyan-300" /><input value={team} onChange={(event) => setTeam(event.target.value)} required maxLength={80} aria-label="Assigned unit" className="w-full min-w-0 bg-transparent outline-none" /></span></span>
            </label>
            <label className="flex min-h-14 items-center justify-between gap-3 rounded-lg bg-[#0a0e18] px-3 py-2">
              <span className="block w-full"><span className="block text-[10px] text-slate-400">Target Audience</span><select value={audience} onChange={(event) => setAudience(event.target.value)} aria-label="Target audience" className="mt-1 w-full bg-transparent text-xs text-indigo-200 outline-none">{['marketing', 'programs', 'shared', 'student_success'].map((value) => <option key={value} value={value} className="bg-[#171b26] text-white">{value.replaceAll('_', ' ')}</option>)}</select></span>
            </label>
          </div>
          <button type="submit" disabled={!file || workingId === 'upload'} className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-300 to-cyan-500 px-4 text-sm font-semibold text-[#003640] shadow-lg shadow-cyan-500/10 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50">
            {workingId === 'upload' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {workingId === 'upload' ? 'Uploading asset...' : 'Upload Asset'}
          </button>
        </form>}

        <section className="space-y-3">
          <label className="flex h-11 items-center gap-3 rounded-xl bg-[#1c1f2a] px-3.5 text-slate-400">
            <Search className="h-4 w-4 shrink-0" />
            <input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Filter by clip name, team, audience..." aria-label="Search video assets" className="min-w-0 flex-1 bg-transparent text-sm text-[#dfe2f1] outline-none placeholder:text-slate-500" />
            <SlidersHorizontal className="h-4 w-4 shrink-0" />
          </label>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {([
              ['all', `All Clips (${assets.length})`],
              ['marketing', 'Marketing'],
              ['raw', 'Raw Takes'],
              ['pending', 'Pending Transcription'],
              ['approved', 'Approved'],
            ] as const).map(([filter, label]) => <button key={filter} type="button" onClick={() => setAssetFilter(filter)} aria-pressed={assetFilter === filter} className={`shrink-0 rounded-full px-3.5 py-2 text-[11px] font-medium transition ${assetFilter === filter ? 'bg-cyan-300 text-[#003640]' : 'bg-[#1c1f2a] text-slate-300 hover:bg-[#262a35] hover:text-white'}`}>{label}</button>)}
          </div>
          <details className="group rounded-xl border border-white/[0.04] bg-[#171b26]">
            <summary className="flex cursor-pointer list-none items-center gap-2 px-3.5 py-3 text-xs font-semibold text-slate-300">
              <SlidersHorizontal className="h-4 w-4 text-slate-400" />Advanced filters and integrations
              <span className="ml-auto text-[10px] font-normal text-slate-500 group-open:hidden">Team · audience · owner · Canva</span>
            </summary>
            <div className="grid gap-3 border-t border-white/[0.05] p-3.5 sm:grid-cols-2 lg:grid-cols-4">
              <label className="block"><span className="mb-1 block text-[10px] text-slate-400">Team filter</span><select value={teamFilter} onChange={(event) => setTeamFilter(event.target.value)} className="h-10 w-full rounded-lg border border-white/[0.05] bg-[#0a0e18] px-3 text-xs text-white"><option value="">All teams</option><option value="videographer">Videographer</option><option value="marketing">Marketing</option></select></label>
              <label className="block"><span className="mb-1 block text-[10px] text-slate-400">Audience filter</span><select value={audienceFilter} onChange={(event) => setAudienceFilter(event.target.value)} className="h-10 w-full rounded-lg border border-white/[0.05] bg-[#0a0e18] px-3 text-xs text-white"><option value="">All audiences</option>{['marketing', 'programs', 'shared', 'student_success'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select></label>
              <label className="block"><span className="mb-1 block text-[10px] text-slate-400">Owner ID</span><input value={ownerFilter} onChange={(event) => setOwnerFilter(event.target.value)} placeholder="Optional user UUID" className="h-10 w-full rounded-lg border border-white/[0.05] bg-[#0a0e18] px-3 text-xs text-white placeholder:text-slate-500" /></label>
              {canUseCanva && <div className="flex items-end text-xs text-slate-300">Canva: {canvaConnected ? 'connected' : canvaConfigured ? 'ready to connect' : 'not configured'}</div>}
            </div>
            {canUseCanva && <details className="border-t border-white/[0.05] px-3.5 py-3">
              <summary className="cursor-pointer text-xs font-semibold text-slate-300">Canva template mapping</summary>
              <div className="mt-3 grid gap-3 md:grid-cols-[1fr_2fr]">
                <label><span className="mb-1 block text-[10px] text-slate-400">Brand Template ID</span><input value={canvaTemplateId} onChange={(event) => setCanvaTemplateId(event.target.value)} className="h-10 w-full rounded-lg border border-white/[0.05] bg-[#0a0e18] px-3 text-xs text-white" /></label>
                <label><span className="mb-1 block text-[10px] text-slate-400">Autofill data JSON (supports {'{{title}}'}, {'{{caption}}'}, {'{{hook}}'})</span><textarea rows={3} value={canvaData} onChange={(event) => setCanvaData(event.target.value)} className="w-full rounded-lg border border-white/[0.05] bg-[#0a0e18] px-3 py-2 font-mono text-xs text-white" /></label>
              </div>
            </details>}
          </details>
        </section>

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold tracking-tight text-[#dfe2f1]">Active Ingests</h2>
              <span className="rounded-full bg-[#262a35] px-2 py-1 text-[10px] text-cyan-300">{visibleAssets.length} shown</span>
            </div>
            {loading && <span className="text-xs text-slate-400">Syncing assets...</span>}
          </div>
          {visibleAssets.map((asset) => <article key={asset.id} className="space-y-3 rounded-2xl border border-white/[0.04] bg-[#1c1f2a] p-3.5 shadow-[0_8px_24px_rgba(2,6,23,0.2)] sm:p-4">
            <div className="flex flex-wrap items-start gap-3">
              <div className="relative flex h-[76px] w-24 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-white/[0.06] bg-[radial-gradient(circle_at_30%_25%,rgba(76,215,246,0.22),transparent_45%),linear-gradient(145deg,#0a0e18,#171b26)] text-cyan-300">
                <FileVideo2 className="h-8 w-8 opacity-80" />
                <span className="absolute bottom-1.5 right-1.5 rounded bg-[#0a0e18]/90 px-1.5 py-0.5 text-[9px] text-slate-300">{asset.mime_type.split('/').pop()?.toUpperCase() || 'MEDIA'}</span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="truncate text-sm font-semibold text-[#dfe2f1]">{asset.title}</h3>
                    <p className="mt-1 truncate font-mono text-[10px] text-slate-400">{asset.original_filename}</p>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-[10px] capitalize ${asset.transcript ? 'bg-emerald-400/10 text-emerald-300' : 'bg-indigo-300/10 text-indigo-200'}`}>{asset.status.replaceAll('_', ' ')}</span>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-slate-400">
                  <span>{fileSize(asset.size_bytes)}</span><span>·</span><span className="text-cyan-300">{asset.team}</span><span>·</span><span className="text-indigo-200">{asset.audience}</span>
                  {asset.created_at && <><span>·</span><span>{new Date(asset.created_at).toLocaleDateString()}</span></>}
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                {canEdit && !asset.transcript && <button type="button" disabled={Boolean(workingId)} onClick={() => void runAction(asset, 'transcribe')} className="inline-flex min-h-10 items-center gap-1.5 rounded-lg border border-slate-700 px-3 text-xs font-semibold text-slate-200 transition hover:border-cyan-400/50 hover:text-cyan-200 disabled:opacity-50"><Clapperboard className="h-3.5 w-3.5" />Transcribe</button>}
                {canEdit && asset.transcript && <button type="button" disabled={Boolean(workingId)} onClick={() => void runAction(asset, 'generate-clips')} className="inline-flex min-h-10 items-center gap-1.5 rounded-lg bg-cyan-400/10 px-3 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-400/20 disabled:opacity-50"><Sparkles className="h-3.5 w-3.5" />Generate clips</button>}
              </div>
            </div>
            {asset.transcript && <details className="rounded-xl bg-[#0a0e18] px-3 py-2.5"><summary className="cursor-pointer text-xs font-semibold text-slate-300">Transcript · {asset.transcript_provider || 'provider unknown'}</summary><p className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap border-l border-slate-700 pl-3 text-xs leading-5 text-slate-400">{asset.transcript}</p></details>}
            {asset.generated_outputs?.length > 0 && <div className="space-y-3 border-t border-white/[0.05] pt-3">{asset.generated_outputs.map((output, outputIndex) => {
              const isWorking = workingId === `${asset.id}-${outputIndex}`
              return <div key={`${output.title}-${outputIndex}`} className="rounded-xl bg-[#0a0e18] p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h4 className="text-sm font-semibold text-slate-100">{output.title}</h4><span className="rounded-full bg-[#262a35] px-2 py-1 text-[10px] uppercase text-slate-300">{output.status}</span></div><p className="mt-1 text-xs text-slate-400">{output.start_seconds.toFixed(1)}s–{output.end_seconds.toFixed(1)}s{output.rationale ? ` · ${output.rationale}` : ''}</p></div>
                  <div className="flex flex-wrap gap-2">
                    {canApprove && output.status === 'draft' && <><button type="button" disabled={Boolean(workingId)} onClick={() => void reviewOutput(asset, outputIndex, 'approved')} title="Approve clip" aria-label="Approve clip" className="flex h-10 w-10 items-center justify-center rounded-lg border border-emerald-800 text-emerald-300 transition hover:bg-emerald-950 disabled:opacity-50"><Check className="h-4 w-4" /></button><button type="button" disabled={Boolean(workingId)} onClick={() => void reviewOutput(asset, outputIndex, 'rejected')} title="Reject clip" aria-label="Reject clip" className="flex h-10 w-10 items-center justify-center rounded-lg border border-rose-900 text-rose-300 transition hover:bg-rose-950 disabled:opacity-50"><X className="h-4 w-4" /></button></>}
                    {canUseCanva && canEdit && output.status === 'approved' && <button type="button" disabled={Boolean(workingId) || !canvaConnected} onClick={() => void (output.canva ? pollCanvaDesign(asset, outputIndex) : createCanvaDesign(asset, output, outputIndex))} className="min-h-10 rounded-lg border border-slate-700 px-3 text-xs font-semibold text-slate-200 disabled:opacity-50">{isWorking ? 'Working...' : output.canva ? `Check Canva · ${output.canva.status}` : 'Create Canva design'}</button>}
                    {canPublish && output.status === 'approved' && <><select aria-label={`Publish ${output.title} to`} value={channel} onChange={(event) => setChannel(event.target.value)} className="min-h-10 rounded-lg border border-slate-700 bg-[#171b26] px-2 text-xs text-white">{['instagram', 'facebook', 'linkedin', 'tiktok', 'youtube'].map((value) => <option key={value} value={value}>{value}</option>)}</select><button type="button" disabled={Boolean(workingId)} onClick={() => void publish(asset, outputIndex)} className="inline-flex min-h-10 items-center gap-1.5 rounded-lg bg-slate-100 px-3 text-xs font-semibold text-slate-900 disabled:opacity-50">{isWorking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Video className="h-3.5 w-3.5" />}Publish</button></>}
                  </div>
                </div>
                {output.hook && <p className="mt-2 text-xs font-medium text-cyan-200">{output.hook}</p>}
                {output.caption && <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-300">{output.caption}</p>}
                {output.review_note && <p className="mt-2 text-[11px] text-slate-500">Review: {output.review_note}</p>}
                {output.canva?.edit_url && <a href={output.canva.edit_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-cyan-300 underline">Open Canva design</a>}
                {output.published_url && <a href={output.published_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-cyan-300 underline">View published asset</a>}
              </div>
            })}</div>}
          </article>)}
          {!visibleAssets.length && !loading && <div className="flex min-h-36 flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-700 bg-[#171b26] px-4 text-center text-sm text-slate-400"><Video className="h-6 w-6 text-slate-500" />No video assets match these filters.</div>}
        </section>

        {canApprove && <section className="rounded-2xl border border-white/[0.04] bg-[#1c1f2a] p-4 sm:p-5">
          <div className="flex items-center gap-2"><CheckCircle2 className="h-5 w-5 text-emerald-300" /><h2 className="text-sm font-semibold text-[#dfe2f1]">Review & handoff</h2></div>
          <p className="mt-1 text-xs text-slate-400">This note is attached when you approve or reject a clip.</p>
          <label className="mt-3 block"><span className="sr-only">Approval or rejection note</span><input value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} minLength={3} maxLength={1000} className="h-11 w-full rounded-lg border border-white/[0.05] bg-[#0a0e18] px-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400/60" /></label>
        </section>}
      </div>
    </div>
  )
}