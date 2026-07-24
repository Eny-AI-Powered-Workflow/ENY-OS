// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/lib/permissions.ts
import { useSession } from '@supabase/auth-helpers-react'
import { useMemo } from 'react'

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
  const { data: session } = useSession()

  // Get user roles from session metadata
  const userRoles = useMemo(() => {
    return session?.user?.user_metadata?.roles as string[] || []
  }, [session])

  // Role to permissions mapping based on the seed data in 0001_init_rbac.sql
  const rolePermissions = useMemo(() => {
    return {
      'ceo': ['leads:read', 'leads:write', 'pipeline:read', 'agents:trigger', 'agents:configure', 'students:read', 'students:write'],
      'programs_manager': ['students:read', 'students:write', 'pipeline:read'],
      'customer_success': ['students:read', 'students:write'],
      'business_support': [], // Will be populated when content scopes exist
      'executive_assistant': ['pipeline:read', 'agents:trigger'],
      'enrollment': ['leads:read', 'leads:write', 'pipeline:read'],
      'developer': ['agents:trigger', 'agents:configure']
    }
  }, [])

  // Calculate all permissions for the user based on their roles
  const permissions = useMemo(() => {
    const perms: string[] = []
    userRoles.forEach(role => {
      const rolePerms = rolePermissions[role]
      if (rolePerms) {
        perms.push(...rolePerms)
      }
    })
    // Remove duplicates while preserving order
    return [...new Set(perms)]
  }, [userRoles, rolePermissions])

  // Function to check if user has a specific permission
  const can = (permission: string) => {
    return permissions.includes(permission)
  }

  // Function to check if user has all required permissions
  const canAll = (permissions: string[]) => {
    return permissions.every(p => can(p))
  }

  // Function to check if user has any of the permissions
  const canAny = (permissions: string[]) => {
    return permissions.some(p => can(p))
  }

  return {
    permissions,
    userRoles,
    can,
    canAll,
    canAny
  }
}