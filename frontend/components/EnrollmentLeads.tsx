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
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center">
            <Users className="mr-2 h-4 w-4" />
            <CardTitle className="text-xl">Leads</CardTitle>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search leads..."
              value={searchTerm}
              onChange={(event) => {
                setSearchTerm(event.target.value)
                setOffset(0)
              }}
              className="rounded border py-1.5 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-brass-500"
            />
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          GHL remains the source of lead records; ENY tracks team ownership and assignment history.
        </p>
        <div className="flex gap-2 pt-2" role="tablist" aria-label="Lead views">
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
              className={`rounded-lg px-3 py-2 text-xs font-semibold ${
                view === key ? 'bg-slate-900 text-white' : 'border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            <Users className="h-5 w-5" />
            Loading leads...
          </div>
        ) : leads.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground">{view === 'mine' ? 'No leads are assigned to you yet.' : 'No leads found.'}</p>
            {searchTerm && <p className="mt-2 text-xs text-muted-foreground">No leads match &quot;{searchTerm}&quot;.</p>}
          </div>
        ) : leads.map((lead) => {
          const currentAssignment = lead.assigned_user_id && lead.assigned_department
            ? `${lead.assigned_department}:${lead.assigned_user_id}`
            : ''
          const assigneeName = teamMembers.find(
            (member) => member.id === lead.assigned_user_id && member.department === lead.assigned_department,
          )?.name
          const canManageOwner = canManageDepartment(lead.assigned_department)

          return (
            <article key={lead.id} className="rounded-lg border p-4 transition-shadow hover:shadow-md">
              <div className="flex flex-col justify-between gap-3 sm:flex-row">
                <div className="min-w-0">
                  <h3 className="truncate font-semibold text-foreground">{lead.name || `${lead.firstName} ${lead.lastName}`}</h3>
                  <p className="truncate text-sm text-muted-foreground">{lead.email || 'No email'}</p>
                  {lead.phone && <p className="text-xs text-muted-foreground">{lead.phone}</p>}
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
                <div className="flex flex-col items-start gap-2 sm:items-end">
                  <span className="text-xs text-muted-foreground">Score: {lead.score ?? 'N/A'}</span>
                  {canAssign && canManageOwner ? (
                    <select
                      aria-label={`Assign ${lead.name || lead.id}`}
                      value={currentAssignment}
                      disabled={assigningId === lead.id || teamMembers.length === 0}
                      onChange={(event) => void assignLead(lead, event.target.value)}
                      className="max-w-64 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 disabled:bg-slate-50"
                    >
                      <option value="">{lead.assigned_user_id ? 'Assignee unavailable' : 'Assign lead'}</option>
                      {teamMembers.map((member) => (
                        <option key={`${member.department}-${member.id}`} value={`${member.department}:${member.id}`}>
                          {member.name} · {member.department === 'sales' ? 'Sales' : 'Enrollment'}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span className="text-xs text-slate-600">
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
        {!loading && (
          <div className="flex items-center justify-between border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={() => setOffset((current) => Math.max(0, current - pageSize))}
              disabled={offset === 0}
              className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-xs text-slate-500">Page {Math.floor(offset / pageSize) + 1}</span>
            <button
              type="button"
              onClick={() => setOffset((current) => current + pageSize)}
              disabled={!hasMore}
              className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
