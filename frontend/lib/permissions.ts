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
  children?: Module[]
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
    permissions: ['leads:read', 'leads:write', 'pipeline:read'],
    children: [
      { name: 'All Leads', href: '/dashboard/enrollment', icon: 'LayoutDashboard', permissions: ['leads:read'] },
      { name: 'Hot Leads', href: '/dashboard/enrollment/hot-leads', icon: 'Flame', permissions: ['leads:read'] },
      { name: 'Approved Work', href: '/dashboard/enrollment/approved-work', icon: 'ListChecks', permissions: ['leads:read'] },
      { name: 'Lead Operations', href: '/dashboard/enrollment/lead-operations', icon: 'Workflow', permissions: ['leads:read'] },
    ]
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
    permissions: ['marketing:read']
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
  },
  {
    name: 'ENY AI Desk',
    href: '/dashboard/ai-desk',
    icon: 'Sparkles',
    permissions: ['ai:chat']
  },
  {
    name: 'Executive Assistant',
    href: '/dashboard/executive-assistant',
    icon: 'BriefcaseBusiness',
    permissions: ['assistant:briefing:read']
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
    ceo: ['leads:read', 'leads:write', 'pipeline:read', 'agents:trigger', 'agents:configure', 'students:read', 'students:write', 'ai:chat', 'assistant:briefing:read', 'assistant:briefing:write', 'assistant:automation:trigger', 'assistant:research:write', 'marketing:read', 'marketing:write', 'marketing:approve', 'marketing:publish', 'marketing:analytics', 'marketing:configure', 'marketing:research'],
    programs_manager: ['students:read', 'students:write', 'pipeline:read', 'ai:chat'],
    customer_success: ['students:read', 'students:write', 'ai:chat'],
    business_support: ['ai:chat'],
    marketing: ['marketing:read', 'marketing:write', 'marketing:analytics', 'marketing:research'],
    marketing_lead: ['marketing:read', 'marketing:write', 'marketing:approve', 'marketing:publish', 'marketing:analytics', 'marketing:configure', 'marketing:research'],
    executive_assistant: ['pipeline:read', 'agents:trigger', 'ai:chat', 'assistant:briefing:read', 'assistant:briefing:write', 'assistant:automation:trigger', 'assistant:research:write'],
    enrollment: ['leads:read', 'leads:write', 'pipeline:read', 'ai:chat'],
    developer: ['agents:trigger', 'agents:configure', 'ai:chat']
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