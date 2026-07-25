// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/AccessBadge.tsx
'use client'

import { usePermissions } from '@/lib/permissions'

export function AccessBadge() {
  const { userRoles, permissions, can } = usePermissions()

  if (userRoles.length === 0) {
    return <div className="text-xs text-muted-foreground">No roles assigned</div>
  }

  return (
    <div className="space-y-2 text-sm">
      <div className="flex flex-col">
        <div className="font-medium">You are logged in as:</div>
        <div className="flex items-center space-x-2">
          <div className="h-8 w-8 flex items-center justify-center bg-primary text-primary-foreground rounded-md">
            {userRoles[0]?.toUpperCase()?.charAt(0) || 'U'}
          </div>
          <div>
            <div className="font-medium">{userRoles[0]}</div>
            <div className="flex flex-wrap gap-1">
              {userRoles.map((role: string) => (
                <span key={role} className="px-2 py-0.5 text-xs rounded-full bg-primary/10 text-primary">
                  {role}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="border-t pt-3">
        <div className="font-medium mb-2">Your permissions:</div>
        <div className="space-y-1">
          {permissions.map((perm: string) => (
            <div key={perm} className="flex items-center gap-2">
              <div className="h-3 w-3 bg-green-500 rounded"></div>
              <span className="text-xs">{perm}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}