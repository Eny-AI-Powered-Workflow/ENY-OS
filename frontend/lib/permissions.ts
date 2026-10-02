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
    permissions: ['students:read']
  },
  ...(process.env.NEXT_PUBLIC_BUSINESS_SUPPORT_ENABLED === 'true' ? [{
    name: 'Business Support',
    href: '/dashboard/business-support',
    icon: 'ClipboardList',
    permissions: ['business_support:dashboard:read'],
  }] : []),
  {
    name: 'Marketing',
    href: '/dashboard/marketing',
    icon: 'Megaphone',
    permissions: ['marketing:read']
  },
  {
    name: 'Videographer',
    href: '/dashboard/videographer',
    icon: 'Video',
    permissions: ['video:read']
  },
  {
    name: 'Graphic & Funnel Designer',
    href: '/dashboard/designer',
    icon: 'Palette',
    permissions: ['design:workspace']
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
    ceo: ['leads:read', 'leads:write', 'pipeline:read', 'agents:trigger', 'agents:configure', 'students:read', 'students:write', 'ai:chat', 'assistant:briefing:read', 'assistant:briefing:write', 'assistant:automation:trigger', 'assistant:research:write', 'marketing:read', 'marketing:write', 'marketing:approve', 'marketing:publish', 'marketing:analytics', 'marketing:configure', 'marketing:research', 'marketing:send', 'marketing:integrations', 'marketing:approve_sensitive', 'marketing:seo', 'marketing:social', 'video:read', 'video:upload', 'video:edit', 'video:approve', 'video:publish', 'video:team:read:videographer', 'video:team:read:marketing', 'video:team:read:programs', 'video:team:read:student_success', 'marketing:content:read', 'marketing:content:write', 'design:workspace', 'design:manage', 'design:write', 'design:read_marketing', 'design:read_programs', 'design:review_marketing', 'design:review_programs', 'design:templates', 'design:funnels', 'design:analytics', 'design:publish', 'design:request', 'design:publish_marketing', 'design:publish_programs', 'design:ai', 'design:canva', 'payments:kajabi:read', 'payments:paystack:read', 'payments:verify', 'students:attendance:read', 'students:attendance:write', 'students:assignments:read', 'students:intervention:review', 'students:intervention:approve', 'students:course_access:request', 'students:course_access:grant', 'students:course_access:approve', 'business_support:pilot:read', 'business_support:pilot:write'],
    programs_manager: ['students:read', 'pipeline:read', 'ai:chat', 'design:workspace', 'design:read_programs', 'design:review_programs', 'design:request', 'design:publish_programs', 'business_support:dashboard:read', 'business_support:pilot:read', 'payments:kajabi:read', 'payments:paystack:read', 'students:attendance:read', 'students:assignments:read', 'students:intervention:review', 'students:intervention:approve', 'students:course_access:approve'],
    customer_success: ['students:read', 'ai:chat', 'design:workspace', 'design:read_programs', 'design:request', 'payments:kajabi:read', 'payments:paystack:read', 'students:attendance:read', 'students:attendance:write', 'students:assignments:read', 'students:intervention:review', 'students:course_access:request'],
    business_support: ['ai:chat', 'design:workspace', 'design:read_marketing', 'design:request', 'business_support:dashboard:read', 'business_support:pilot:read', 'business_support:pilot:write', 'payments:kajabi:read', 'payments:paystack:read', 'payments:verify', 'students:course_access:grant'],
    marketing: ['marketing:read', 'marketing:write', 'marketing:analytics', 'marketing:research', 'marketing:seo', 'marketing:social', 'video:read', 'video:upload', 'video:edit', 'video:team:read:marketing', 'marketing:content:read', 'marketing:content:write', 'design:workspace', 'design:read_marketing', 'design:request'],
    marketing_lead: ['marketing:read', 'marketing:write', 'marketing:approve', 'marketing:publish', 'marketing:analytics', 'marketing:configure', 'marketing:research', 'marketing:send', 'marketing:integrations', 'marketing:seo', 'marketing:social', 'video:read', 'video:upload', 'video:edit', 'video:approve', 'video:publish', 'video:team:read:marketing', 'marketing:content:read', 'marketing:content:write', 'design:workspace', 'design:read_marketing', 'design:review_marketing', 'design:templates', 'design:funnels', 'design:analytics', 'design:publish', 'design:request', 'design:publish_marketing'],
    videographer: ['video:read', 'video:upload', 'video:edit', 'video:approve', 'video:publish', 'video:team:read:videographer', 'marketing:content:read', 'marketing:content:write', 'design:read_marketing', 'design:canva'],
    graphic_designer: ['design:workspace', 'design:manage', 'design:write', 'design:templates', 'design:funnels', 'design:analytics', 'design:request', 'design:ai', 'design:canva'],
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
    if (userRoles.includes('ceo')) {
      perms.push(...MODULES.flatMap(module => [
        ...module.permissions,
        ...(module.children ?? []).flatMap(child => child.permissions),
      ]))
    }
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