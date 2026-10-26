// C:\Users\Melody\Documents\ENY-OS\frontend\components\EnrollmentLeads.tsx
'use client'

import { useEffect, useState } from 'react'
import { DownloadCloud, RefreshCw, Search, Users } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type Lead = {
  id: string
  firstName: string
  lastName: string
  name: string
  email: string
  phone: string
  score: number | null
  category: string | null
  tags: string[]
  source: string | null
  created_at: string | null
  review_status: string
  assigned_user_id: string | null
  assigned_department: 'sales' | 'enrollment' | null
}

type GhlCursor = {
  start_after_id?: string
  start_after?: string
} | null

type TeamMember = {
  id: string
  name: string
  email: string | null
  department: 'sales' | 'enrollment'
}

type View = 'all' | 'mine'

type CohortPreview = {
  matching_count: number
  contacts_scanned: number
  scan_complete: boolean
}

type CohortPullSummary = {
  batchesCompleted: number
  lastBatch: {
    contactsMatched: number
    contactsQueued: number
    alreadyQueued: number
    pagesScanned: number
  }
  contactsMatched: number
  contactsQueued: number
  alreadyQueued: number
  pagesScanned: number
  hasMore: boolean
  completedAt: string
}

export default function EnrollmentLeads() {
  const { can, isLoading: permissionsLoading, userRoles } = usePermissions()
  const canAssignSales = can('sales:leads:assign')
  const canAssignEnrollment = can('enrollment:leads:assign')
  const canAssign = canAssignSales || canAssignEnrollment
  const [leads, setLeads] = useState<Lead[]>([])
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([])
  const [currentUserId, setCurrentUserId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [createdFrom, setCreatedFrom] = useState('')
  const [createdTo, setCreatedTo] = useState('')
  const [view, setView] = useState<View>('all')
  const [cursorHistory, setCursorHistory] = useState<GhlCursor[]>([null])
  const [nextCursor, setNextCursor] = useState<GhlCursor>(null)
  const [hasMore, setHasMore] = useState(false)
  const [pendingReviewCount, setPendingReviewCount] = useState(0)
  const [readyForScoringCount, setReadyForScoringCount] = useState(0)
  const [assigningId, setAssigningId] = useState<string | null>(null)
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null)
  const [cohortPreview, setCohortPreview] = useState<CohortPreview | null>(null)
  const [previewCursor, setPreviewCursor] = useState<GhlCursor>(null)
  const [previewHasMore, setPreviewHasMore] = useState(false)
  const [cohortCursor, setCohortCursor] = useState<GhlCursor>(null)
  const [cohortHasMore, setCohortHasMore] = useState(false)
  const [cohortPullStarted, setCohortPullStarted] = useState(false)
  const [cohortLoading, setCohortLoading] = useState(false)
  const [cohortOperation, setCohortOperation] = useState<'preview' | 'pull' | null>(null)
  const [cohortMessage, setCohortMessage] = useState<string | null>(null)
  const [cohortPullSummary, setCohortPullSummary] = useState<CohortPullSummary | null>(null)
  const canPullCohort = can('leads:write')
  const pageSize = 50

  useEffect(() => {
    if (!permissionsLoading && !canAssign && userRoles.some((role) => role === 'sales' || role === 'enrollment')) {
      setView('mine')
    }
  }, [canAssign, permissionsLoading, userRoles])

  const fetchLeads = async () => {
    try {
      setLoading(true)
      setError(null)

      const { data: { session } } = await supabase.auth.getSession()
      setCurrentUserId(session?.user.id ?? null)
      const headers: HeadersInit = session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}
      const query = new URLSearchParams({
        limit: String(pageSize),
        search: searchTerm,
        mine: String(view === 'mine'),
      })
      if (sourceFilter.trim()) query.set('source', sourceFilter.trim())
      if (createdFrom) query.set('created_from', createdFrom)
      if (createdTo) query.set('created_to', createdTo)
      const activeCursor = cursorHistory[cursorHistory.length - 1]
      if (activeCursor?.start_after_id) query.set('cursor_id', activeCursor.start_after_id)
      if (activeCursor?.start_after) query.set('cursor_after', activeCursor.start_after)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/leads?${query.toString()}`,
        { headers, credentials: 'include' },
      )
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : `Unable to load leads (${response.status})`)
      }
      setLeads(payload.leads || [])
      setHasMore(Boolean(payload.has_more))
      setNextCursor(payload.next_cursor || null)
      setPendingReviewCount(Number(payload.pending_review_count || 0))
      setReadyForScoringCount(Number(payload.ready_for_scoring_count || 0))
      setLastRefreshedAt(new Date().toLocaleTimeString())

      if (canAssign) {
        const teamResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/team-members`, {
          headers,
          credentials: 'include',
        })
        const teamPayload = await teamResponse.json()
        if (!teamResponse.ok) {
          throw new Error(typeof teamPayload.detail === 'string' ? teamPayload.detail : 'Unable to load assignment team')
        }
        setTeamMembers(teamPayload.members || [])
      } else {
        setTeamMembers([])
      }
    } catch (cause) {
      console.error('Error fetching enrollment leads:', cause)
      setError(cause instanceof Error ? cause.message : 'Unable to load leads')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchLeads()
    const interval = window.setInterval(() => void fetchLeads(), 60_000)
    return () => window.clearInterval(interval)
  }, [searchTerm, sourceFilter, createdFrom, createdTo, view, canAssign, cursorHistory])

  const resetLeadCursor = () => setCursorHistory([null])

  const resetCohort = () => {
    setCohortPreview(null)
    setPreviewCursor(null)
    setPreviewHasMore(false)
    setCohortCursor(null)
    setCohortHasMore(false)
    setCohortPullStarted(false)
    setCohortMessage(null)
    setCohortPullSummary(null)
  }

  const previewCohort = async (continueScan = false) => {
    setCohortLoading(true)
    setCohortOperation('preview')
    setCohortMessage(null)
    if (!continueScan) {
      setPreviewCursor(null)
      setPreviewHasMore(false)
      setCohortPreview(null)
      setCohortCursor(null)
      setCohortHasMore(false)
      setCohortPullStarted(false)
      setCohortPullSummary(null)
    }
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const query = new URLSearchParams()
      if (sourceFilter.trim()) query.set('source', sourceFilter.trim())
      if (createdFrom) query.set('created_from', createdFrom)
      if (createdTo) query.set('created_to', createdTo)
      const activeCursor = continueScan ? previewCursor : null
      if (activeCursor?.start_after_id) query.set('cursor_id', activeCursor.start_after_id)
      if (activeCursor?.start_after) query.set('cursor_after', activeCursor.start_after)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/intake/cohort-preview?${query.toString()}`,
        {
          headers: session?.access_token ? { Authorization: 'Bearer ' + session.access_token } : {},
          credentials: 'include',
        },
      )
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to preview the GHL cohort')
      }
      setPreviewCursor(payload.next_cursor || null)
      setPreviewHasMore(Boolean(payload.has_more))
      setCohortPreview((current) => ({
        matching_count: (continueScan ? current?.matching_count || 0 : 0) + payload.matching_count,
        contacts_scanned: (continueScan ? current?.contacts_scanned || 0 : 0) + payload.contacts_scanned,
        scan_complete: Boolean(payload.scan_complete),
      }))
      setCohortMessage(
        payload.scan_complete
          ? 'Cohort preview complete.'
          : 'Preview is partial; continue scanning to count the full filtered cohort.',
      )
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to preview the GHL cohort')
      setCohortPreview(null)
    } finally {
      setCohortLoading(false)
      setCohortOperation(null)
    }
  }

  const pullCohort = async () => {
    setCohortLoading(true)
    setCohortOperation('pull')
    setCohortMessage(null)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/intake/cohort-pull`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(session?.access_token ? { Authorization: 'Bearer ' + session.access_token } : {}),
        },
        credentials: 'include',
        body: JSON.stringify({
          source: sourceFilter.trim(),
          created_from: createdFrom || null,
          created_to: createdTo || null,
          cursor_id: cohortCursor?.start_after_id || null,
          cursor_after: cohortCursor?.start_after || null,
          limit: 500,
        }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to pull the GHL cohort')
      }
      setCohortCursor(payload.next_cursor || null)
      setCohortHasMore(Boolean(payload.has_more))
      setCohortPullStarted(true)
      setCohortPullSummary((current) => {
        const contactsMatched = Number(payload.contacts_matched || 0)
        const contactsQueued = Number(payload.contacts_queued || 0)
        const alreadyQueued = Number(payload.already_queued || 0)
        const pagesScanned = Number(payload.pages_scanned || 0)
        return {
          batchesCompleted: (current?.batchesCompleted || 0) + 1,
          lastBatch: { contactsMatched, contactsQueued, alreadyQueued, pagesScanned },
          contactsMatched: (current?.contactsMatched || 0) + contactsMatched,
          contactsQueued: (current?.contactsQueued || 0) + contactsQueued,
          alreadyQueued: (current?.alreadyQueued || 0) + alreadyQueued,
          pagesScanned: (current?.pagesScanned || 0) + pagesScanned,
          hasMore: Boolean(payload.has_more),
          completedAt: new Date().toLocaleTimeString(),
        }
      })
      setCohortMessage('Batch completed successfully.')
      await fetchLeads()
    } catch (cause) {
      const reason = cause instanceof Error ? cause.message : 'Unable to pull the GHL cohort'
      setCohortMessage(
        `Could not confirm this batch: ${reason} You can retry it; contact IDs already in the review queue are safely deduplicated.`,
      )
    } finally {
      setCohortLoading(false)
      setCohortOperation(null)
    }
  }

  const assignLead = async (lead: Lead, selection: string) => {
    const [department, assignedUserId] = selection.split(':', 2)
    if (!assignedUserId || (department !== 'sales' && department !== 'enrollment')) return

    setAssigningId(lead.id)
    setError(null)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/leads/${encodeURIComponent(lead.id)}/assignment`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
          },
          credentials: 'include',
          body: JSON.stringify({ assigned_user_id: assignedUserId, department }),
        },
      )
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to assign lead')
      }
      await fetchLeads()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to assign lead')
    } finally {
      setAssigningId(null)
    }
  }

  const canManageDepartment = (department: string | null) => (
    department === 'sales' ? canAssignSales
      : department === 'enrollment' ? canAssignEnrollment
        : canAssign
  )
  const today = new Date().toISOString().slice(0, 10)

  return (
    <Card className="flex h-[min(82vh,900px)] min-h-[640px] w-full flex-col overflow-hidden border-slate-200/80 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
      <CardHeader className="shrink-0 space-y-4 border-b border-slate-100 bg-gradient-to-br from-white via-white to-violet-50/70 px-5 pb-4 pt-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-violet-100 bg-violet-50 text-violet-700 shadow-sm">
              <Users className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <CardTitle className="text-lg text-slate-950">Leads</CardTitle>
              <p className="mt-1 text-xs text-slate-500">Manage and assign your live CRM leads</p>
            </div>
          </div>
          <div className="relative w-full sm:w-56">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              aria-label="Search leads"
              placeholder="Search leads..."
              value={searchTerm}
              onChange={(event) => {
                setSearchTerm(event.target.value)
                resetLeadCursor()
              }}
              className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm text-slate-800 shadow-sm placeholder:text-slate-400 focus:border-violet-400 focus:outline-none focus:ring-4 focus:ring-violet-100"
            />
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-sm text-[11px] leading-4 text-slate-500">
            GHL is the source of lead records; ENY stores team ownership and review status. Refreshes run automatically every minute.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {lastRefreshedAt && <span className="text-[10px] text-slate-500">Last refreshed {lastRefreshedAt}</span>}
            <button
              type="button"
              disabled={loading}
              onClick={() => void fetchLeads()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-violet-200 bg-white px-3 py-2 text-xs font-semibold text-violet-800 hover:bg-violet-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh from GHL
            </button>
          </div>
          <div className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1" role="tablist" aria-label="Lead views">
          {([
            ['all', 'All leads'],
            ['mine', 'My leads'],
          ] as const).map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={view === key}
              onClick={() => {
                setView(key)
                resetLeadCursor()
              }}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                view === key ? 'bg-white text-violet-800 shadow-sm ring-1 ring-slate-200' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              {label}
            </button>
          ))}
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="text-[10px] font-medium text-slate-600">
            GHL source / cohort
            <input
              type="text"
              value={sourceFilter}
              disabled={cohortLoading}
              onChange={(event) => { setSourceFilter(event.target.value); resetLeadCursor(); resetCohort() }}
              placeholder="e.g. webinar, bootcamp"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs disabled:opacity-60"
            />
          </label>
          <label className="text-[10px] font-medium text-slate-600">
            Created from
            <input type="date" value={createdFrom} disabled={cohortLoading} onChange={(event) => { setCreatedFrom(event.target.value); resetLeadCursor(); resetCohort() }} className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs disabled:opacity-60" />
          </label>
          <label className="text-[10px] font-medium text-slate-600">
            Created to
            <input type="date" value={createdTo} disabled={cohortLoading} onChange={(event) => { setCreatedTo(event.target.value); resetLeadCursor(); resetCohort() }} className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs disabled:opacity-60" />
          </label>
        </div>
        {canPullCohort && (
          <div className="rounded-xl border border-violet-100 bg-violet-50/60 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-xs font-semibold text-violet-950">Pull a cohort into review</p>
                <p className="mt-0.5 text-[10px] text-violet-800">Preview matching GHL contacts, then queue IDs for human review. This does not score or contact leads.</p>
              </div>
              <div className="flex gap-2">
                {(!cohortPreview || previewHasMore) && (
                <button type="button" disabled={cohortLoading || (!sourceFilter.trim() && !createdFrom && !createdTo)} onClick={() => void previewCohort(Boolean(cohortPreview && previewHasMore))} className="rounded-lg border border-violet-200 bg-white px-3 py-2 text-xs font-semibold text-violet-800 disabled:opacity-50">
                  {cohortLoading && cohortOperation === 'preview' ? 'Previewing…' : cohortPreview ? 'Continue preview' : 'Preview cohort'}
                </button>
                )}
                {cohortPreview && cohortPreview.matching_count > 0 && (!cohortPullStarted || cohortHasMore) && (
                  <button type="button" disabled={cohortLoading} onClick={() => void pullCohort()} className="inline-flex items-center gap-1.5 rounded-lg bg-violet-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">
                    <DownloadCloud className="h-3.5 w-3.5" />
                    {cohortLoading && cohortOperation === 'pull' ? 'Pulling…' : cohortCursor ? 'Pull next 500' : 'Pull first 500'}
                  </button>
                )}
              </div>
            </div>
            {cohortPreview && <p className="mt-2 text-[10px] text-violet-900">Preview: {cohortPreview.matching_count.toLocaleString()} matches across {cohortPreview.contacts_scanned.toLocaleString()} contacts scanned{cohortPreview.scan_complete ? '' : ' so far'}.</p>}
            {cohortLoading && (
              <div role="status" aria-live="polite" className="mt-3 flex items-center gap-2 rounded-lg border border-violet-200 bg-white px-3 py-2 text-xs text-violet-900">
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                {cohortOperation === 'pull'
                  ? 'Pulling up to 500 matching contacts from GHL and adding new IDs to the review queue. This may take a little while; keep this page open.'
                  : 'Scanning GHL contacts to calculate the matching cohort size.'}
              </div>
            )}
            {cohortMessage && (
              <p
                role={cohortMessage.startsWith('Could not confirm') ? 'alert' : 'status'}
                aria-live={cohortMessage.startsWith('Could not confirm') ? 'assertive' : 'polite'}
                className={`mt-2 rounded-lg border px-3 py-2 text-xs ${
                  cohortMessage.startsWith('Could not confirm')
                    ? 'border-rose-200 bg-rose-50 text-rose-800'
                    : 'border-emerald-200 bg-emerald-50 text-emerald-800'
                }`}
              >
                {cohortMessage}
              </p>
            )}
            {cohortPullSummary && (
              <div className="mt-2 rounded-lg border border-violet-200 bg-white px-3 py-2 text-[10px] text-violet-950">
                <p className="font-semibold">
                  {cohortPullSummary.batchesCompleted} batch{cohortPullSummary.batchesCompleted === 1 ? '' : 'es'} completed
                  {' · '}last completed {cohortPullSummary.completedAt}
                </p>
                <p className="mt-1">
                  Latest batch: {cohortPullSummary.lastBatch.contactsMatched.toLocaleString()} matched
                  {' · '}{cohortPullSummary.lastBatch.contactsQueued.toLocaleString()} newly queued
                  {' · '}{cohortPullSummary.lastBatch.alreadyQueued.toLocaleString()} already queued
                  {' · '}{cohortPullSummary.lastBatch.pagesScanned.toLocaleString()} GHL pages scanned
                </p>
                <p className="mt-1">
                  Total across batches: {cohortPullSummary.contactsQueued.toLocaleString()} newly queued
                  {' · '}{cohortPullSummary.alreadyQueued.toLocaleString()} already queued
                  {' · '}{cohortPullSummary.contactsMatched.toLocaleString()} matched
                  {' · '}{cohortPullSummary.pagesScanned.toLocaleString()} GHL pages scanned
                </p>
                <p className="mt-1 font-medium">
                  {cohortPullSummary.hasMore
                    ? 'More matching contacts remain. Select “Pull next 500” to continue.'
                    : 'No additional matching contacts remain for this filtered pull.'}
                </p>
              </div>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden px-5 pb-4 pt-4">
        {error && <p role="alert" className="mb-3 shrink-0 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
        <div className="mb-3 flex shrink-0 flex-wrap gap-x-4 gap-y-1 text-[10px] text-slate-600">
          <span>Loaded from GHL: <strong>{leads.length}</strong></span>
          <span>New today on this page: <strong>{leads.filter((lead) => lead.created_at?.slice(0, 10) === today).length}</strong></span>
          <span>Unassigned on this page: <strong>{leads.filter((lead) => !lead.assigned_user_id).length}</strong></span>
          <span>Assigned to you: <strong>{leads.filter((lead) => lead.assigned_user_id === currentUserId).length}</strong></span>
          <span>Queued for review: <strong>{pendingReviewCount}</strong></span>
          <span>Ready for scoring: <strong>{readyForScoringCount}</strong></span>
          {leads.some((lead) => lead.source) && <span>Sources shown: <strong>{Array.from(new Set(leads.map((lead) => lead.source).filter(Boolean))).join(', ')}</strong></span>}
        </div>
        {loading ? (
          <div className="flex min-h-0 flex-1 items-center justify-center gap-2 text-sm text-slate-500">
            <Users className="h-5 w-5 text-violet-500" />
            Loading leads…
          </div>
        ) : leads.length === 0 ? (
          <div className="flex min-h-0 flex-1 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-5 text-center">
            <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-white text-slate-400 shadow-sm ring-1 ring-slate-200">
              <Users className="h-5 w-5" />
            </span>
            <p className="text-sm font-medium text-slate-700">{view === 'mine' ? 'No leads are assigned to you yet.' : 'No leads found.'}</p>
            {searchTerm && <p className="mt-2 text-xs text-slate-500">No leads match &quot;{searchTerm}&quot;.</p>}
          </div>
        ) : (
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain pr-1 [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin]">
          {leads.map((lead) => {
          const currentAssignment = lead.assigned_user_id && lead.assigned_department
            ? `${lead.assigned_department}:${lead.assigned_user_id}`
            : ''
          const assigneeName = teamMembers.find(
            (member) => member.id === lead.assigned_user_id && member.department === lead.assigned_department,
          )?.name
          const canManageOwner = canManageDepartment(lead.assigned_department)

          return (
            <article key={lead.id} className="rounded-xl border border-slate-200 bg-white p-4 transition duration-200 hover:border-violet-200 hover:shadow-[0_8px_24px_rgba(15,23,42,0.07)]">
              <div className="flex flex-col justify-between gap-3 sm:flex-row">
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-semibold text-slate-900">{lead.name || `${lead.firstName} ${lead.lastName}`}</h3>
                  <p className="mt-1 truncate text-xs text-slate-500">{lead.email || 'No email'}</p>
                  {lead.phone && <p className="mt-0.5 text-xs text-slate-500">{lead.phone}</p>}
                  <p className="mt-1 text-[10px] text-slate-500">
                    {lead.source ? `Source: ${lead.source}` : 'Source: unknown'}
                    {lead.created_at ? ` · Added ${new Date(lead.created_at).toLocaleDateString()}` : ''}
                  </p>
                  <p className="mt-1 text-[10px] font-medium text-violet-700">
                    Review · {lead.review_status.replaceAll('_', ' ')}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {lead.tags?.map((tag, index) => (
                      <span
                        key={`${lead.id}-${tag}-${index}`}
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          tag.toLowerCase().includes('hot')
                            ? 'bg-red-100 text-red-800'
                            : tag.toLowerCase().includes('follow')
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-600">Score · {lead.score ?? 'N/A'}</span>
                  {canAssign && canManageOwner ? (
                    <select
                      aria-label={`Assign ${lead.name || lead.id}`}
                      value={currentAssignment}
                      disabled={assigningId === lead.id || teamMembers.length === 0}
                      onChange={(event) => void assignLead(lead, event.target.value)}
                      className="max-w-64 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-700 shadow-sm focus:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-100 disabled:bg-slate-50"
                    >
                      <option value="">{lead.assigned_user_id ? 'Assignee unavailable' : 'Assign lead'}</option>
                      {teamMembers.map((member) => (
                        <option key={`${member.department}-${member.id}`} value={`${member.department}:${member.id}`}>
                          {member.name} · {member.department === 'sales' ? 'Sales' : 'Enrollment'}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span className="text-xs font-medium text-slate-600">
                      {lead.assigned_user_id
                        ? `${lead.assigned_user_id === currentUserId ? 'Assigned to you' : assigneeName || 'Assigned'}${lead.assigned_department ? ` · ${lead.assigned_department}` : ''}`
                        : 'Unassigned'}
                    </span>
                  )}
                </div>
              </div>
            </article>
          )
          })}
          </div>
        )}
        {!loading && (
          <div className="mt-3 flex shrink-0 items-center justify-between border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={() => setCursorHistory((current) => current.length > 1 ? current.slice(0, -1) : current)}
              disabled={cursorHistory.length <= 1}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-xs font-medium tabular-nums text-slate-500">Page {cursorHistory.length}</span>
            <button
              type="button"
              onClick={() => nextCursor && setCursorHistory((current) => [...current, nextCursor])}
              disabled={!hasMore || !nextCursor}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
