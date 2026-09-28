'use client'

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { Archive, CheckCircle2, Clock3, FileImage, FileText, Loader2, Plus, RefreshCw, Send, ShieldCheck, Upload } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'

type Audience = 'shared' | 'marketing' | 'programs' | 'student_success'
type Foundation = { id: string; title: string; audience: Audience; version: number; authoritative: boolean }
type DesignRequest = { id: string; title: string; brief: string; request_type: string; audience: Audience; status: string; requester_id: string; owner_id: string | null; due_at: string | null; campaign_name: string | null; program_name: string | null; source_content_id: string | null; source_video_asset_id: string | null }
type Template = { id: string; template_key: string; title: string; category: string; audience: Audience; provider: string; template_url: string | null; provider_template_id: string | null; status: string; version: number; base_brand_document_id: string; base_brand_version: number; stale: boolean; locked_fields: string[]; locked_values: Record<string, unknown>; editable_fields: string[]; usage_rights: Record<string, unknown> }
type AssetFile = { id: string; file_kind: string; provider: string; original_filename: string; mime_type: string; size_bytes: number }
type Asset = { id: string; title: string; asset_type: string; provider: string; audience: Audience; status: string; request_id: string | null; template_id: string | null; template_version: number | null; template_stale: boolean; brand_document_id: string; brand_version: number; brand_stale: boolean; campaign_name: string | null; program_name: string | null; source_content_id: string | null; source_video_asset_id: string | null; usage_rights: Record<string, unknown>; revision: number; files: AssetFile[] }
type History = { versions: Array<Record<string, unknown>>; events: Array<{ event_type: string; details: Record<string, unknown>; created_at: string | null }> }

const audienceLabels: Record<Audience, string> = { shared: 'Shared', marketing: 'Marketing', programs: 'Programs', student_success: 'Student Success' }
const requestTypes = ['social_graphic', 'email_header', 'webinar_promotion', 'video_thumbnail', 'quote_card', 'certificate', 'program_material', 'funnel_asset', 'other']
const assetTypes = ['social_graphic', 'email_header', 'webinar_promotion', 'video_thumbnail', 'quote_card', 'certificate', 'program_material', 'funnel_asset', 'other']
const defaultUsageRights = JSON.stringify({ rights_basis: 'ENY-created original', permitted_uses: ['social', 'email', 'web'], attribution: null, expires_at: null }, null, 2)

type Tab = 'requests' | 'templates' | 'assets'

export default function DesignProductionWorkspace() {
  const [tab, setTab] = useState<Tab>('requests')
  const [permissions, setPermissions] = useState<string[]>([])
  const [currentUserId, setCurrentUserId] = useState('')
  const [foundation, setFoundation] = useState<Foundation[]>([])
  const [requests, setRequests] = useState<DesignRequest[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [previewLinks, setPreviewLinks] = useState<Record<string, string>>({})
  const [history, setHistory] = useState<{ title: string; data: History } | null>(null)
  const [activeFileAsset, setActiveFileAsset] = useState<string | null>(null)
  const addFileInput = useRef<HTMLInputElement>(null)

  const [requestForm, setRequestForm] = useState({ title: '', brief: '', request_type: 'social_graphic', audience: 'marketing' as Audience, due_at: '', campaign_name: '', program_name: '', source_content_id: '', source_video_asset_id: '' })
  const [templateForm, setTemplateForm] = useState({ template_key: '', title: '', category: 'social_graphic', audience: 'marketing' as Audience, template_url: '', provider_template_id: '', base_brand_document_id: '', locked_fields: 'logo, brand_colors, typography', locked_values: '{}', editable_fields: 'headline, body, image', rights_basis: '' })
  const [assetForm, setAssetForm] = useState({ title: '', asset_type: 'social_graphic', audience: 'marketing' as Audience, request_id: '', template_id: '', brand_document_id: '', file_kind: 'export', campaign_name: '', program_name: '', source_content_id: '', source_video_asset_id: '', variant_values: '{}', usage_rights: defaultUsageRights })
  const [assetFile, setAssetFile] = useState<File | null>(null)

  const has = (scope: string) => permissions.includes(scope)
  const brandOptions = useMemo(() => foundation.filter((item) => item.authoritative), [foundation])
  const audienceBrandOptions = (audience: Audience) => brandOptions.filter((item) => item.audience === audience || item.audience === 'shared')
  const templateOptions = useMemo(() => templates.filter((item) => item.status === 'approved' && !item.stale), [templates])

  const headers = async (json = false): Promise<HeadersInit> => {
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.user?.id) setCurrentUserId(session.user.id)
    return { ...(json ? { 'Content-Type': 'application/json' } : {}), ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}) }
  }

  const load = async () => {
    setLoading(true)
    try {
      const requestHeaders = await headers()
      const base = process.env.NEXT_PUBLIC_API_URL
      const [foundationResponse, requestResponse, assetResponse, templateResponse] = await Promise.all([
        fetch(`${base}/api/v1/designer/foundation`, { headers: requestHeaders, credentials: 'include' }),
        fetch(`${base}/api/v1/designer/requests`, { headers: requestHeaders, credentials: 'include' }),
        fetch(`${base}/api/v1/designer/assets`, { headers: requestHeaders, credentials: 'include' }),
        fetch(`${base}/api/v1/designer/templates`, { headers: requestHeaders, credentials: 'include' }).catch(() => null),
      ])
      const foundationPayload = await foundationResponse.json()
      if (!foundationResponse.ok) throw new Error(typeof foundationPayload.detail === 'string' ? foundationPayload.detail : 'Unable to load Designer workspace')
      setFoundation(foundationPayload.documents || [])
      setPermissions(foundationPayload.permissions || [])
      if (requestResponse.ok) setRequests((await requestResponse.json()).requests || [])
      if (assetResponse.ok) setAssets((await assetResponse.json()).assets || [])
      if (templateResponse?.ok) setTemplates((await templateResponse.json()).templates || [])
      setMessage(null)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load Designer workspace')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const createRequest = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = {
        ...requestForm,
        due_at: requestForm.due_at ? new Date(requestForm.due_at).toISOString() : null,
        campaign_name: requestForm.campaign_name || null,
        program_name: requestForm.program_name || null,
        source_content_id: requestForm.source_content_id || null,
        source_video_asset_id: requestForm.source_video_asset_id || null,
        reference_urls: [],
      }
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/requests`, { method: 'POST', headers: await headers(true), credentials: 'include', body: JSON.stringify(payload) })
      const result = await response.json()
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Unable to submit design request')
      setMessage('Design request submitted and assigned to the Designer queue.')
      setRequestForm({ title: '', brief: '', request_type: 'social_graphic', audience: 'marketing', due_at: '', campaign_name: '', program_name: '', source_content_id: '', source_video_asset_id: '' })
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to submit design request')
    } finally {
      setSaving(false)
    }
  }

  const changeRequestStatus = async (request: DesignRequest, status: 'in_progress' | 'in_review') => {
    const note = window.prompt(`Note for ${status.replaceAll('_', ' ')}:`)
    if (!note || note.trim().length < 3) return
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/requests/${request.id}`, { method: 'PATCH', headers: await headers(true), credentials: 'include', body: JSON.stringify({ status, owner_id: status === 'in_progress' ? currentUserId : request.owner_id, due_at: request.due_at, note }) })
    const payload = await response.json()
    setMessage(response.ok ? `Request moved to ${status.replaceAll('_', ' ')}.` : (typeof payload.detail === 'string' ? payload.detail : 'Request update failed'))
    await load()
  }

  const createTemplate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const brand = brandOptions.find((item) => item.id === templateForm.base_brand_document_id)
    if (!brand) { setMessage('Select approved, audience-compatible brand guidance first.'); return }
    setSaving(true)
    try {
      const payload = {
        template_key: templateForm.template_key.trim().toLowerCase().replaceAll(' ', '-'), title: templateForm.title,
        category: templateForm.category, audience: templateForm.audience, provider: 'manual_canva',
        provider_template_id: templateForm.provider_template_id || null, template_url: templateForm.template_url || null,
        base_brand_document_id: brand.id, base_brand_version: brand.version,
        locked_fields: templateForm.locked_fields.split(',').map((item) => item.trim()).filter(Boolean),
        locked_values: JSON.parse(templateForm.locked_values),
        editable_fields: templateForm.editable_fields.split(',').map((item) => item.trim()).filter(Boolean),
        usage_rights: { rights_basis: templateForm.rights_basis, permitted_uses: ['social', 'email', 'web'], attribution: null },
      }
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/templates`, { method: 'POST', headers: await headers(true), credentials: 'include', body: JSON.stringify(payload) })
      const result = await response.json()
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Unable to create template')
      setMessage('Template draft saved with its locked fields and approved brand version.')
      setTemplateForm({ template_key: '', title: '', category: 'social_graphic', audience: 'marketing', template_url: '', provider_template_id: '', base_brand_document_id: '', locked_fields: 'logo, brand_colors, typography', locked_values: '{}', editable_fields: 'headline, body, image', rights_basis: '' })
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to create template')
    } finally {
      setSaving(false)
    }
  }

  const templateAction = async (template: Template, action: 'submit' | 'approve' | 'changes' | 'revise') => {
    if (template.audience === 'shared' && !canManage && action !== 'submit' && action !== 'revise') { setMessage('Only Designer owners or the CEO can review shared templates.'); return }
    if (action === 'revise') {
      const title = window.prompt('Revised template title', template.title)
      if (!title) return
      const changeNote = window.prompt('Describe the template revision:')
      if (!changeNote) return
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/templates/${template.id}`, { method: 'PATCH', headers: await headers(true), credentials: 'include', body: JSON.stringify({ title, template_url: template.template_url, provider_template_id: template.provider_template_id, base_brand_document_id: template.base_brand_document_id, base_brand_version: template.base_brand_version, locked_fields: template.locked_fields, locked_values: template.locked_values, editable_fields: template.editable_fields, usage_rights: template.usage_rights, change_note: changeNote }) })
      const result = await response.json()
      setMessage(response.ok ? `Template revision ${result.version} saved as draft.` : (typeof result.detail === 'string' ? result.detail : 'Template revision failed'))
      await load()
      return
    }
    const note = window.prompt(action === 'approve' ? 'Approval note:' : action === 'changes' ? 'Required changes:' : 'Submission note:')
    if (!note || note.trim().length < 3) return
    const isMarketing = template.audience === 'marketing' || template.audience === 'shared'
    let url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/templates/${template.id}`
    let method = 'POST'
    let body: Record<string, unknown> = { note }
    if (action === 'submit') url += '/submit'
    if (action === 'approve') { url += `/approve-${isMarketing ? 'marketing' : 'programs'}`; body = { note, source_verified: window.confirm('Confirm the template has usage rights and matches the currently approved brand source.') } }
    if (action === 'changes') url += `/request-${isMarketing ? 'marketing' : 'program'}-changes`
    const form = new FormData()
    if (action === 'submit') form.append('note', note)
    const response = await fetch(url, { method, headers: action === 'submit' ? await headers() : await headers(true), credentials: 'include', body: action === 'submit' ? form : JSON.stringify(body) })
    const result = await response.json()
    setMessage(response.ok ? (action === 'approve' ? 'Template approved and locked to its brand version.' : action === 'changes' ? 'Template returned to draft.' : 'Template submitted for review.') : (typeof result.detail === 'string' ? result.detail : 'Template workflow action failed'))
    await load()
  }

  const createAsset = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!assetFile) { setMessage('Choose an export or source file first.'); return }
    const brand = brandOptions.find((item) => item.id === assetForm.brand_document_id)
    if (!brand) { setMessage('Select approved brand guidance for the asset.'); return }
    const template = templateOptions.find((item) => item.id === assetForm.template_id)
    if (assetForm.template_id && !template) { setMessage('Select a current approved template.'); return }
    const form = new FormData()
    form.append('file', assetFile)
    form.append('title', assetForm.title)
    form.append('asset_type', assetForm.asset_type)
    form.append('audience', assetForm.audience)
    form.append('brand_document_id', brand.id)
    form.append('brand_version', String(brand.version))
    form.append('usage_rights_json', assetForm.usage_rights)
    form.append('variant_values_json', assetForm.variant_values)
    form.append('file_kind', assetForm.file_kind)
    if (assetForm.request_id) form.append('request_id', assetForm.request_id)
    if (template) { form.append('template_id', template.id); form.append('template_version', String(template.version)) }
    if (assetForm.campaign_name) form.append('campaign_name', assetForm.campaign_name)
    if (assetForm.program_name) form.append('program_name', assetForm.program_name)
    if (assetForm.source_content_id) form.append('source_content_id', assetForm.source_content_id)
    if (assetForm.source_video_asset_id) form.append('source_video_asset_id', assetForm.source_video_asset_id)
    setSaving(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/assets`, { method: 'POST', headers: await headers(), credentials: 'include', body: form })
      const result = await response.json()
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Unable to save design asset')
      setMessage('Asset saved privately as a draft with source, rights, request, template, and brand-version traceability.')
      setAssetFile(null)
      setAssetForm({ title: '', asset_type: 'social_graphic', audience: 'marketing', request_id: '', template_id: '', brand_document_id: '', file_kind: 'export', campaign_name: '', program_name: '', source_content_id: '', source_video_asset_id: '', variant_values: '{}', usage_rights: defaultUsageRights })
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to save design asset')
    } finally {
      setSaving(false)
    }
  }

  const submitAsset = async (asset: Asset) => {
    const note = window.prompt('Review context for this export:')
    if (!note) return
    const form = new FormData(); form.append('note', note)
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/assets/${asset.id}/submit`, { method: 'POST', headers: await headers(), credentials: 'include', body: form })
    const result = await response.json()
    setMessage(response.ok ? 'Asset submitted for audience approval.' : (typeof result.detail === 'string' ? result.detail : 'Asset submission failed'))
    await load()
  }

  const reviewAsset = async (asset: Asset, approve: boolean) => {
    if (asset.audience === 'shared' && !canManage) { setMessage('Only Designer owners or the CEO can review shared assets.'); return }
    const note = window.prompt(approve ? 'Approval note:' : 'Required corrections:')
    if (!note || note.trim().length < 5) return
    const marketingAudience = asset.audience === 'marketing' || asset.audience === 'shared'
    const endpoint = approve
      ? `/approve-${marketingAudience ? 'marketing' : 'programs'}`
      : `/request-changes-${marketingAudience ? 'marketing' : 'programs'}`
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/assets/${asset.id}${endpoint}`, { method: 'POST', headers: await headers(true), credentials: 'include', body: JSON.stringify({ note, source_verified: approve && window.confirm('Confirm this export follows the approved brand version and usage rights.') }) })
    const result = await response.json()
    setMessage(response.ok ? (approve ? 'Asset approved.' : 'Asset returned to the Designer with a reason.') : (typeof result.detail === 'string' ? result.detail : 'Asset review failed'))
    await load()
  }

  const publishAsset = async (asset: Asset) => {
    if (asset.audience === 'shared' && !canManage) { setMessage('Only Designer owners or the CEO can publish shared assets.'); return }
    const permission = asset.audience === 'marketing' ? 'design:publish_marketing' : ['programs', 'student_success'].includes(asset.audience) ? 'design:publish_programs' : 'design:publish'
    if (!has(permission)) { setMessage('Your role cannot publish this audience’s asset.'); return }
    const confirmPublish = window.confirm(`Record ${asset.title} as published for ${audienceLabels[asset.audience]}?`)
    if (!confirmPublish) return
    const endpoint = asset.audience === 'marketing' ? 'publish-marketing' : ['programs', 'student_success'].includes(asset.audience) ? 'publish-programs' : 'publish-shared'
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/assets/${asset.id}/${endpoint}`, { method: 'POST', headers: await headers(), credentials: 'include' })
    const result = await response.json()
    setMessage(response.ok ? 'Publication recorded in the asset audit history.' : (typeof result.detail === 'string' ? result.detail : 'Asset publication failed'))
    await load()
  }

  const previewFile = async (asset: Asset, file: AssetFile) => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/assets/${asset.id}/files/${file.id}/preview`, { headers: await headers(), credentials: 'include' })
    const result = await response.json()
    if (!response.ok) { setMessage(typeof result.detail === 'string' ? result.detail : 'Unable to create preview link'); return }
    setPreviewLinks((previous) => ({ ...previous, [file.id]: result.signed_url }))
  }

  const showHistory = async (kind: 'requests' | 'templates' | 'assets', id: string, title: string) => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/${kind}/${id}/history`, { headers: await headers(), credentials: 'include' })
    const result = await response.json()
    if (!response.ok) { setMessage(typeof result.detail === 'string' ? result.detail : 'Unable to load workflow history'); return }
    setHistory({ title, data: result })
  }

  const addFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    const assetId = activeFileAsset
    if (!file || !assetId) return
    const note = window.prompt('Revision note for this new file:')
    if (!note || note.trim().length < 3) { event.target.value = ''; return }
    const form = new FormData(); form.append('file', file); form.append('file_kind', 'export'); form.append('change_note', note)
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/assets/${assetId}/files`, { method: 'POST', headers: await headers(), credentials: 'include', body: form })
    const result = await response.json()
    setMessage(response.ok ? `New revision ${result.revision} uploaded; approval has been reset.` : (typeof result.detail === 'string' ? result.detail : 'File upload failed'))
    event.target.value = ''
    setActiveFileAsset(null)
    await load()
  }

  const canManage = has('design:manage')
  const canRequest = has('design:request')
  const canAddTemplates = has('design:templates')
  const selectedRequest = requests.find((item) => item.id === assetForm.request_id)
  const compatibleBrandDocs = audienceBrandOptions(assetForm.audience)
  const compatibleTemplateList = templateOptions.filter((item) => item.audience === assetForm.audience || item.audience === 'shared')

  return (
    <section className="space-y-5 rounded-[20px] border border-slate-200 bg-white p-5 text-slate-900 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-[10px] uppercase tracking-[0.2em] text-teal-700">Graphic & Funnel Designer</p><h2 className="mt-1 text-2xl font-semibold">Requests, templates, and assets</h2><p className="mt-2 max-w-2xl text-sm text-slate-600">Private files; explicit audience approvals; every export stays tied to its request, usage rights, template revision, and approved brand version.</p></div><button type="button" onClick={() => void load()} title="Refresh design production" className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600"><RefreshCw className={loading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} /></button></div>
      {message && <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">{message}</p>}
      <div className="flex gap-2 border-b border-slate-200 pb-3">{(['requests', 'templates', 'assets'] as Tab[]).map((value) => <button key={value} type="button" onClick={() => setTab(value)} className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize ${tab === value ? 'bg-slate-900 text-white' : 'border border-slate-200 text-slate-600'}`}>{value}</button>)}</div>

      {tab === 'requests' && <div className="space-y-4">
        {canRequest && <form onSubmit={createRequest} className="grid gap-3 rounded-xl border border-teal-100 bg-teal-50/50 p-4 md:grid-cols-2">
          <label><span className="mb-1 block text-xs font-semibold">Request title</span><input required minLength={3} maxLength={240} value={requestForm.title} onChange={(e) => setRequestForm({ ...requestForm, title: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Type</span><select value={requestForm.request_type} onChange={(e) => setRequestForm({ ...requestForm, request_type: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">{requestTypes.map((item) => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}</select></label>
          <label><span className="mb-1 block text-xs font-semibold">Audience</span><select value={requestForm.audience} onChange={(e) => setRequestForm({ ...requestForm, audience: e.target.value as Audience })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">{Object.entries(audienceLabels).filter(([key]) => key !== 'shared' || canManage).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label><span className="mb-1 block text-xs font-semibold">Due date</span><input type="datetime-local" value={requestForm.due_at} onChange={(e) => setRequestForm({ ...requestForm, due_at: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Campaign association</span><input value={requestForm.campaign_name} onChange={(e) => setRequestForm({ ...requestForm, campaign_name: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Program association</span><input value={requestForm.program_name} onChange={(e) => setRequestForm({ ...requestForm, program_name: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label className="md:col-span-2"><span className="mb-1 block text-xs font-semibold">Design brief</span><textarea required minLength={10} maxLength={10000} rows={4} value={requestForm.brief} onChange={(e) => setRequestForm({ ...requestForm, brief: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <div className="flex justify-end md:col-span-2"><button disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-teal-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}Submit request</button></div>
        </form>}
        <div className="grid gap-3 lg:grid-cols-2">{requests.map((item) => <article key={item.id} className="rounded-xl border border-slate-200 p-4"><div className="flex justify-between gap-3"><div><h3 className="font-semibold">{item.title}</h3><p className="mt-1 text-xs uppercase text-slate-500">{item.request_type.replaceAll('_', ' ')} · {audienceLabels[item.audience]} · {item.status.replaceAll('_', ' ')}</p></div><span className="text-xs text-slate-500">{item.due_at ? new Date(item.due_at).toLocaleDateString() : 'No due date'}</span></div><p className="mt-3 line-clamp-4 whitespace-pre-wrap text-sm text-slate-600">{item.brief}</p><p className="mt-2 text-xs text-slate-500">{item.campaign_name ? `Campaign: ${item.campaign_name}` : ''}{item.program_name ? ` · Program: ${item.program_name}` : ''}</p>{canManage && item.status === 'requested' && <div className="mt-3 flex gap-2"><button type="button" onClick={() => void changeRequestStatus(item, 'in_progress')} className="rounded-md border border-cyan-200 px-2.5 py-1.5 text-xs font-semibold text-cyan-800">Assign to me</button><button type="button" onClick={() => void changeRequestStatus(item, 'in_review')} className="rounded-md border border-amber-200 px-2.5 py-1.5 text-xs font-semibold text-amber-800">Move to review</button></div>}</article>)}</div>
        {!requests.length && !loading && <p className="py-5 text-center text-sm text-slate-500">No design requests are visible to this account.</p>}
      </div>}

      {tab === 'templates' && <div className="space-y-4">
        {canAddTemplates && <form onSubmit={createTemplate} className="grid gap-3 rounded-xl border border-cyan-100 bg-cyan-50/50 p-4 md:grid-cols-2">
          <label><span className="mb-1 block text-xs font-semibold">Template key</span><input required value={templateForm.template_key} onChange={(e) => setTemplateForm({ ...templateForm, template_key: e.target.value })} placeholder="social-quote-card" className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Template name</span><input required value={templateForm.title} onChange={(e) => setTemplateForm({ ...templateForm, title: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Audience</span><select value={templateForm.audience} onChange={(e) => setTemplateForm({ ...templateForm, audience: e.target.value as Audience, base_brand_document_id: '' })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">{Object.entries(audienceLabels).filter(([key]) => key !== 'shared' || canManage).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label><span className="mb-1 block text-xs font-semibold">Approved brand version</span><select required value={templateForm.base_brand_document_id} onChange={(e) => setTemplateForm({ ...templateForm, base_brand_document_id: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"><option value="">Choose approved source</option>{audienceBrandOptions(templateForm.audience).map((doc) => <option key={doc.id} value={doc.id}>{doc.title} · v{doc.version}</option>)}</select></label>
          <label><span className="mb-1 block text-xs font-semibold">Canva template URL</span><input type="url" value={templateForm.template_url} onChange={(e) => setTemplateForm({ ...templateForm, template_url: e.target.value })} placeholder="https://www.canva.com/design/..." className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Provider template ID (optional)</span><input value={templateForm.provider_template_id} onChange={(e) => setTemplateForm({ ...templateForm, provider_template_id: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Locked fields, comma separated</span><input value={templateForm.locked_fields} onChange={(e) => setTemplateForm({ ...templateForm, locked_fields: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label className="md:col-span-2"><span className="mb-1 block text-xs font-semibold">Exact locked field values (JSON)</span><textarea required value={templateForm.locked_values} onChange={(e) => setTemplateForm({ ...templateForm, locked_values: e.target.value })} rows={3} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-xs" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Editable fields, comma separated</span><input value={templateForm.editable_fields} onChange={(e) => setTemplateForm({ ...templateForm, editable_fields: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label className="md:col-span-2"><span className="mb-1 block text-xs font-semibold">Usage rights basis</span><input required value={templateForm.rights_basis} onChange={(e) => setTemplateForm({ ...templateForm, rights_basis: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <div className="flex justify-end md:col-span-2"><button disabled={saving || !brandOptions.length} className="rounded-lg bg-cyan-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Save manual template</button></div>
        </form>}
        <div className="grid gap-3 lg:grid-cols-2">{templates.map((template) => { const canReviewTemplate = template.status === 'in_review' && ((has('design:review_marketing') && ['marketing', 'shared'].includes(template.audience)) || (has('design:review_programs') && ['programs', 'student_success', 'shared'].includes(template.audience))); return <article key={template.id} className="rounded-xl border border-slate-200 p-4"><div className="flex justify-between gap-3"><div><h3 className="font-semibold">{template.title}</h3><p className="mt-1 text-xs uppercase text-slate-500">{template.category} · {audienceLabels[template.audience]} · v{template.version}</p></div><span className={`text-xs font-semibold ${template.stale ? 'text-rose-700' : template.status === 'approved' ? 'text-emerald-700' : 'text-slate-500'}`}>{template.stale ? 'Brand version stale' : template.status.replaceAll('_', ' ')}</span></div><p className="mt-2 text-xs text-slate-600">Locked: {template.locked_fields.join(', ') || 'none'}<br />Editable: {template.editable_fields.join(', ') || 'none'}</p><div className="mt-3 flex flex-wrap gap-2">{template.template_url && <a href={template.template_url} target="_blank" rel="noreferrer" className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold">Open Canva</a>}{canManage && ['draft', 'in_review', 'approved'].includes(template.status) && <button type="button" onClick={() => void templateAction(template, 'revise')} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs">New version</button>}{canAddTemplates && template.status === 'draft' && <button type="button" onClick={() => void templateAction(template, 'submit')} className="rounded-md border border-cyan-200 px-2.5 py-1.5 text-xs text-cyan-800">Submit review</button>}{canReviewTemplate && <button type="button" onClick={() => void templateAction(template, 'approve')} className="rounded-md border border-emerald-200 px-2.5 py-1.5 text-xs text-emerald-800">Approve</button>}{canReviewTemplate && <button type="button" onClick={() => void templateAction(template, 'changes')} className="rounded-md border border-amber-200 px-2.5 py-1.5 text-xs text-amber-800">Request changes</button>}</div></article>})}</div>
        {!templates.length && !loading && <p className="py-5 text-center text-sm text-slate-500">No templates are available for this role. Create one from approved brand guidance.</p>}
      </div>}

      {tab === 'assets' && <div className="space-y-4">
        {canManage && <form onSubmit={createAsset} className="grid gap-3 rounded-xl border border-rose-100 bg-rose-50/40 p-4 md:grid-cols-2">
          <label><span className="mb-1 block text-xs font-semibold">Asset title</span><input required value={assetForm.title} onChange={(e) => setAssetForm({ ...assetForm, title: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Asset type</span><select value={assetForm.asset_type} onChange={(e) => setAssetForm({ ...assetForm, asset_type: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">{assetTypes.map((item) => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}</select></label>
          <label><span className="mb-1 block text-xs font-semibold">Audience</span><select value={assetForm.audience} onChange={(e) => setAssetForm({ ...assetForm, audience: e.target.value as Audience, brand_document_id: '', template_id: '' })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">{Object.entries(audienceLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label><span className="mb-1 block text-xs font-semibold">Approved brand version</span><select required value={assetForm.brand_document_id} onChange={(e) => setAssetForm({ ...assetForm, brand_document_id: e.target.value, template_id: '' })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"><option value="">Choose source</option>{compatibleBrandDocs.map((doc) => <option key={doc.id} value={doc.id}>{doc.title} · v{doc.version}</option>)}</select></label>
          <label><span className="mb-1 block text-xs font-semibold">Request association</span><select value={assetForm.request_id} onChange={(e) => setAssetForm({ ...assetForm, request_id: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"><option value="">None</option>{requests.filter((item) => item.audience === assetForm.audience && !['completed', 'cancelled'].includes(item.status)).map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
          <label><span className="mb-1 block text-xs font-semibold">Approved template (locks a specific version)</span><select value={assetForm.template_id} onChange={(e) => setAssetForm({ ...assetForm, template_id: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"><option value="">No template</option>{compatibleTemplateList.filter((item) => item.base_brand_document_id === assetForm.brand_document_id).map((item) => <option key={item.id} value={item.id}>{item.title} · v{item.version}</option>)}</select></label>
          {assetForm.template_id && <label className="md:col-span-2"><span className="mb-1 block text-xs font-semibold">Editable variant values (JSON; locked values cannot be overridden)</span><textarea required value={assetForm.variant_values} onChange={(e) => setAssetForm({ ...assetForm, variant_values: e.target.value })} rows={3} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-xs" /></label>}
          <label><span className="mb-1 block text-xs font-semibold">Campaign</span><input value={assetForm.campaign_name} onChange={(e) => setAssetForm({ ...assetForm, campaign_name: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Program</span><input value={assetForm.program_name} onChange={(e) => setAssetForm({ ...assetForm, program_name: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Marketing content ID (optional)</span><input value={assetForm.source_content_id} onChange={(e) => setAssetForm({ ...assetForm, source_content_id: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">Video pack ID (optional)</span><input value={assetForm.source_video_asset_id} onChange={(e) => setAssetForm({ ...assetForm, source_video_asset_id: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /></label>
          <label><span className="mb-1 block text-xs font-semibold">File kind</span><select value={assetForm.file_kind} onChange={(e) => setAssetForm({ ...assetForm, file_kind: e.target.value })} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"><option value="export">Export</option><option value="source">Source</option><option value="preview">Preview</option></select></label>
          <label><span className="mb-1 block text-xs font-semibold">File (PNG, JPEG, WebP, PDF, MP4)</span><input type="file" accept="image/png,image/jpeg,image/webp,application/pdf,video/mp4" required onChange={(e) => setAssetFile(e.target.files?.[0] || null)} className="w-full text-xs" /></label>
          <label className="md:col-span-2"><span className="mb-1 block text-xs font-semibold">Usage rights JSON</span><textarea required value={assetForm.usage_rights} onChange={(e) => setAssetForm({ ...assetForm, usage_rights: e.target.value })} rows={3} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-xs" /></label>
          {selectedRequest && <p className="text-xs text-slate-500 md:col-span-2">Request: {selectedRequest.title} · {selectedRequest.request_type}</p>}
          <div className="flex justify-end md:col-span-2"><button disabled={saving || !assetFile} className="inline-flex items-center gap-2 rounded-lg bg-rose-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}Save private draft</button></div>
        </form>}
        <input ref={addFileInput} type="file" accept="image/png,image/jpeg,image/webp,application/pdf,video/mp4" className="hidden" onChange={(e) => void addFile(e)} />
        <div className="grid gap-3 lg:grid-cols-2">{assets.map((asset) => { const canReviewAsset = asset.status === 'in_review' && ((has('design:review_marketing') && ['marketing', 'shared'].includes(asset.audience)) || (has('design:review_programs') && ['programs', 'student_success', 'shared'].includes(asset.audience))); const publishPermission = asset.audience === 'marketing' ? 'design:publish_marketing' : ['programs', 'student_success'].includes(asset.audience) ? 'design:publish_programs' : 'design:publish'; return <article key={asset.id} className="rounded-xl border border-slate-200 p-4"><div className="flex justify-between gap-3"><div><h3 className="font-semibold">{asset.title}</h3><p className="mt-1 text-xs uppercase text-slate-500">{asset.asset_type.replaceAll('_', ' ')} · {audienceLabels[asset.audience]} · r{asset.revision}</p></div><span className={`text-xs font-semibold ${asset.status === 'published' ? 'text-emerald-700' : asset.status === 'rejected' || asset.brand_stale || asset.template_stale ? 'text-rose-700' : 'text-slate-500'}`}>{asset.brand_stale ? 'Brand source stale' : asset.template_stale ? 'Template stale' : asset.status.replaceAll('_', ' ')}</span></div><p className="mt-2 text-xs text-slate-500">Brand v{asset.brand_version}{asset.template_id ? ` · template v${asset.template_version}` : ''}{asset.campaign_name ? ` · ${asset.campaign_name}` : ''}{asset.program_name ? ` · ${asset.program_name}` : ''}</p><div className="mt-3 space-y-2">{asset.files.map((file) => <div key={file.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-slate-50 p-2 text-xs"><span>{file.file_kind} · {file.original_filename} · {(file.size_bytes / 1048576).toFixed(1)} MB</span>{previewLinks[file.id] ? <a href={previewLinks[file.id]} target="_blank" rel="noreferrer" className="font-semibold text-cyan-800">Open private preview</a> : <button type="button" onClick={() => void previewFile(asset, file)} className="font-semibold text-cyan-800">Create preview link</button>}</div>)}</div><div className="mt-3 flex flex-wrap gap-2">{canManage && ['draft', 'rejected'].includes(asset.status) && <><button type="button" onClick={() => void submitAsset(asset)} className="rounded-md border border-cyan-200 px-2.5 py-1.5 text-xs text-cyan-800">Submit review</button><button type="button" onClick={() => { setActiveFileAsset(asset.id); addFileInput.current?.click() }} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs">Add revision file</button></>}{canReviewAsset && <button type="button" onClick={() => void reviewAsset(asset, true)} className="inline-flex items-center gap-1 rounded-md border border-emerald-200 px-2.5 py-1.5 text-xs text-emerald-800"><CheckCircle2 className="h-3.5 w-3.5" />Approve</button>}{canReviewAsset && <button type="button" onClick={() => void reviewAsset(asset, false)} className="rounded-md border border-amber-200 px-2.5 py-1.5 text-xs text-amber-800">Request changes</button>}{asset.status === 'approved' && (canManage || has(publishPermission)) && <button type="button" onClick={() => void publishAsset(asset)} className="inline-flex items-center gap-1 rounded-md border border-violet-200 px-2.5 py-1.5 text-xs text-violet-800"><Send className="h-3.5 w-3.5" />Record publish</button>}</div></article>})}</div>
        {!assets.length && !loading && <p className="py-5 text-center text-sm text-slate-500">No design assets are visible to this account.</p>}
      </div>}
      <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3">
        {tab === 'requests' && requests.map((item) => <button key={item.id} type="button" onClick={() => void showHistory('requests', item.id, item.title)} className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700"><Clock3 className="h-3.5 w-3.5" />Request history · {item.title}</button>)}
        {tab === 'templates' && templates.map((item) => <button key={item.id} type="button" onClick={() => void showHistory('templates', item.id, item.title)} className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700"><Clock3 className="h-3.5 w-3.5" />Template history · {item.title}</button>)}
        {tab === 'assets' && assets.map((item) => <button key={item.id} type="button" onClick={() => void showHistory('assets', item.id, item.title)} className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700"><Clock3 className="h-3.5 w-3.5" />Asset history · {item.title}</button>)}
      </div>
      {history && <div className="rounded-xl border border-slate-200 bg-slate-50 p-4"><div className="flex items-center justify-between gap-3"><h3 className="font-semibold">Workflow history · {history.title}</h3><button type="button" onClick={() => setHistory(null)} className="rounded-md border border-slate-200 px-2 py-1 text-xs">Close</button></div><div className="mt-3 space-y-2">{history.data.versions.map((version, index) => <div key={`v-${index}`} className="rounded-md bg-white p-2 text-xs"><p className="font-semibold">Version/revision {String(version.version ?? version.revision ?? '')} · {String(version.change_note || '')}</p></div>)}{history.data.events.map((event, index) => <div key={`e-${index}`} className="border-t border-slate-200 pt-2 text-xs"><span className="font-semibold">{event.event_type.replaceAll('_', ' ')}</span><span className="ml-2 text-slate-500">{event.created_at ? new Date(event.created_at).toLocaleString() : ''}</span><p className="mt-1 text-slate-600">{Object.entries(event.details || {}).filter(([, value]) => typeof value === 'string').map(([key, value]) => `${key.replaceAll('_', ' ')}: ${value}`).join(' · ')}</p></div>)}</div></div>}
    </section>
  )
}
