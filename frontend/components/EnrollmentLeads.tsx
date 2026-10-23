// C:\Users\Melody\Documents\ENY-OS\frontend\components\EnrollmentLeads.tsx
'use client'

import { useEffect, useState } from 'react'
import { Search, Users } from 'lucide-react'
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
  assigned_user_id: string | null
  assigned_department: 'sales' | 'enrollment' | null
}

type TeamMember = {
  id: string
  name: string
  email: string | null
  department: 'sales' | 'enrollment'
}

type View = 'all' | 'mine'

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
  const [view, setView] = useState<View>('all')
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [assigningId, setAssigningId] = useState<string | null>(null)
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
        offset: String(offset),
        search: searchTerm,
        mine: String(view === 'mine'),
      })
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
  }, [searchTerm, view, canAssign, offset])

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

  return (
    <Card className="flex h-[min(72vh,760px)] min-h-[520px] w-full flex-col overflow-hidden border-slate-200/80 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
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
                setOffset(0)
              }}
              className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm text-slate-800 shadow-sm placeholder:text-slate-400 focus:border-violet-400 focus:outline-none focus:ring-4 focus:ring-violet-100"
            />
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-sm text-[11px] leading-4 text-slate-500">
            GHL is the source of lead records; ENY tracks team ownership and assignment history.
          </p>
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
                setOffset(0)
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
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden px-5 pb-4 pt-4">
        {error && <p role="alert" className="mb-3 shrink-0 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
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
        {!loading && leads.length > 0 && (
          <div className="mt-3 flex shrink-0 items-center justify-between border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={() => setOffset((current) => Math.max(0, current - pageSize))}
              disabled={offset === 0}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-xs font-medium tabular-nums text-slate-500">Page {Math.floor(offset / pageSize) + 1}</span>
            <button
              type="button"
              onClick={() => setOffset((current) => current + pageSize)}
              disabled={!hasMore}
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
