// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/AccessBadge.tsx
'use client'

import { useState } from 'react'
import { ChevronDown, ShieldCheck, UserRound } from 'lucide-react'
import { usePermissions } from '@/lib/permissions'

export function AccessBadge() {
  const [permissionsExpanded, setPermissionsExpanded] = useState(false)
  const { session, userRoles, permissions } = usePermissions()
  const email = session?.user?.email
  const displayName = String(
    session?.user?.user_metadata?.full_name
      || session?.user?.user_metadata?.name
      || email?.split('@')[0]
      || userRoles[0]
      || 'ENY User'
  )
  const initials = displayName
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('') || 'U'
  const permissionsPanelId = 'assigned-permissions-list'

  return (
    <div className="space-y-3 text-sm text-slate-100">
      <section aria-label="Signed-in profile" className="rounded-xl border border-slate-700/80 bg-gradient-to-br from-slate-800/90 to-slate-900/90 p-3 shadow-sm">
        <div className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
          <UserRound className="h-3.5 w-3.5 text-violet-300" />
          <span>Signed-in profile</span>
        </div>
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/15 bg-gradient-to-br from-violet-400 via-violet-500 to-indigo-600 text-sm font-bold tracking-wide text-white shadow-[0_6px_18px_rgba(139,92,246,0.25)]">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-white" title={displayName}>{displayName}</div>
            {email && <div className="mt-0.5 truncate text-[11px] text-slate-400" title={email}>{email}</div>}
            <div className="mt-2 flex flex-wrap gap-1.5">
              {userRoles.length > 0 ? userRoles.map((role: string) => (
                <span
                  key={role}
                  className="rounded-full border border-violet-300/20 bg-violet-400/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.12em] text-violet-200"
                >
                  {role}
                </span>
              )) : <span className="text-[11px] text-slate-400">No roles assigned</span>}
            </div>
          </div>
        </div>
      </section>

      <section aria-label="Assigned permissions" className="overflow-hidden rounded-xl border border-slate-700/80 bg-slate-900/70">
        <button
          type="button"
          aria-expanded={permissionsExpanded}
          aria-controls={permissionsPanelId}
          onClick={() => setPermissionsExpanded((expanded) => !expanded)}
          className="group flex w-full items-center gap-3 p-3 text-left transition hover:bg-slate-800/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-violet-400"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-emerald-400/20 bg-emerald-400/10 text-emerald-300">
            <ShieldCheck className="h-4 w-4" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-xs font-semibold text-slate-100">Your permissions</span>
            <span className="mt-0.5 block text-[10px] text-slate-400">
              {permissionsExpanded ? 'Hide assigned scopes' : 'Review assigned scopes'}
            </span>
          </span>
          <span className="shrink-0 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 text-[10px] font-semibold tabular-nums text-emerald-300">
            {permissions.length} active
          </span>
          <ChevronDown className={`h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200 group-hover:text-slate-200 ${permissionsExpanded ? 'rotate-180' : ''}`} />
        </button>

        <div id={permissionsPanelId} hidden={!permissionsExpanded} className="border-t border-slate-800 px-3 pb-3 pt-2">
          {permissions.length > 0 ? (
            <div className="max-h-56 space-y-1 overflow-y-auto pr-1 [scrollbar-color:rgb(71_85_105)_transparent] [scrollbar-width:thin]">
              {permissions.map((perm: string) => (
                <div key={perm} className="flex items-start gap-2 rounded-lg border border-white/[0.04] bg-white/[0.03] px-2.5 py-2">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                  <span className="break-words text-[11px] leading-4 text-slate-300">{perm}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-lg bg-white/[0.03] px-2.5 py-2 text-[11px] text-slate-400">
              No permission scopes assigned.
            </p>
          )}
        </div>
      </section>
    </div>
  )
}