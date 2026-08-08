// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/AccessBadge.tsx
'use client'

import { usePermissions } from '@/lib/permissions'

export function AccessBadge() {
  const { userRoles, permissions } = usePermissions()

  if (userRoles.length === 0) {
    return <div className="text-xs text-slate-300/80">No roles assigned</div>
  }

  return (
    <div className="space-y-3 text-sm text-slate-100">
      <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3">
        <p className="mb-2 text-[10px] uppercase tracking-[0.2em] text-slate-400">Account</p>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 text-sm font-bold text-slate-950">
            {userRoles[0]?.toUpperCase()?.charAt(0) || 'U'}
          </div>
          <div className="min-w-0">
            <div className="truncate font-semibold text-white">{userRoles[0]}</div>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {userRoles.map((role: string) => (
                <span
                  key={role}
                  className="rounded-full border border-amber-400/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.16em] text-amber-200"
                >
                  {role}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-slate-900/50 p-3">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Your permissions</p>
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
            {permissions.length} active
          </span>
        </div>
        <div className="space-y-1.5">
          {permissions.map((perm: string) => (
            <div key={perm} className="flex items-center gap-2 rounded-md bg-white/5 px-2 py-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-gradient-to-r from-amber-400 to-orange-500" />
              <span className="text-xs text-slate-200">{perm}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}