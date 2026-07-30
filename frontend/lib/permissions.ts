// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/lib/permissions.ts
'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabaseClient'

// Define the modules and their required permissions
export interface Module {
  name: string
  href: string
  icon: string  // We'll use lucide icons
  permissions: string[] // Array of permission scopes required to access this module
}

// These are the modules from the brief, mapped to their primary roles and permissions
export const MODULES: Module[] = [
  {
    name: 'CEO Cockpit',
    href: '/dashboard/ceo',
    icon: 'Monitor',
    permissions: ['pipeline:read', 'agents:configure']
  },
  {
    name: 'Sales & Enrollment',
    href: '/dashboard/enrollment',
    icon: 'Users',
    permissions: ['leads:read', 'leads:write', 'pipeline:read']
  },
  {
    name: 'Student Success',
    href: '/dashboard/student-success',
    icon: 'GraduationCap',
    permissions: ['students:read', 'students:write']
  },
  {
    name: 'Marketing',
    href: '/dashboard/marketing',
    icon: 'Megaphone',
    permissions: [] // Will be filled when content scopes are added
  },
  {
    name: 'Operations',
    href: '/dashboard/operations',
    icon: 'Settings',
    permissions: [] // Will be filled when ops scopes are added
  },
  {
    name: 'Writer & SOPs',
    href: '/dashboard/writer',
    icon: 'Pencil',
    permissions: ['agents:trigger']
  }
]

// Helper function to check if a user has a specific permission
export function usePermissions() {
  const [session, setSession] = useState<any>(null)
  const [userRoles, setUserRoles] = useState<string[]>([])
  const [permissions, setPermissions] = useState<string[]>([])

  useEffect(() => {
    // Only run in browser environment
    if (typeof window !== 'undefined') {
      // Get initial session
      supabase.auth.getSession().then(({ data: { session } }) => {
        setSession(session)
        if (session?.user?.user_metadata?.roles) {
          setUserRoles(session.user.user_metadata.roles as string[])
        } else {
          setUserRoles([])
        }
      }).catch(() => {
        setUserRoles([])
      })

      // Listen for auth changes
      const {
        data: { subscription },
      } = supabase.auth.onAuthStateChange((_event, session) => {
        setSession(session)
        if (session?.user?.user_metadata?.roles) {
          setUserRoles(session.user.user_metadata.roles as string[])
        } else {
          setUserRoles([])
        }
      })

      // Cleanup
      return () => subscription.unsubscribe()
    }
  }, [])

  // Calculate permissions from userRoles
  // Role to permissions mapping based on the seed data in 0001_init_rbac.sql
  const rolePermissions = {
    ceo: ['leads:read', 'leads:write', 'pipeline:read', 'agents:trigger', 'agents:configure', 'students:read', 'students:write'],
    programs_manager: ['students:read', 'students:write', 'pipeline:read'],
    customer_success: ['students:read', 'students:write'],
    business_support: [], // Will be populated when content scopes exist
    executive_assistant: ['pipeline:read', 'agents:trigger'],
    enrollment: ['leads:read', 'leads:write', 'pipeline:read'],
    developer: ['agents:trigger', 'agents:configure']
  }

  // Calculate all permissions for the user based on their roles
  useEffect(() => {
    const perms: string[] = []
    userRoles.forEach(role => {
      const rolePerms = rolePermissions[role as keyof typeof rolePermissions]
      if (rolePerms) {
        perms.push(...rolePerms)
      }
    })
    // Remove duplicates while preserving order
    const uniquePerms = Array.from(new Set(perms))
    setPermissions(uniquePerms)
  }, [userRoles])

  // Function to check if user has a specific permission
  const can = (permission: string) => {
    return permissions.includes(permission)
  }

  // Function to check if user has all required permissions
  const canAll = (permissionsToCheck: string[]) => {
    return permissionsToCheck.every(p => can(p))
  }

  // Function to check if user has any of the permissions
  const canAny = (permissionsToCheck: string[]) => {
    return permissionsToCheck.some(p => can(p))
  }

  return {
    permissions,
    userRoles,
    can,
    canAll,
    canAny
  }
}