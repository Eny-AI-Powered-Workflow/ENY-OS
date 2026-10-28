// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/lib/permissions.ts
'use client'

import { createContext, createElement, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabaseClient'

// Define the modules and their required permissions
export interface Module {
  name: string
  href: string
  icon: string  // We'll use lucide icons
  permissions: string[] // Array of permission scopes required to access this module
  children?: Module[]
}

export const CEO_COCKPIT_SECTIONS = [
  { id: 'overview', label: 'Overview', icon: 'BarChart3' },
  { id: 'sales', label: 'Sales operations', icon: 'Users' },
  { id: 'briefing', label: 'Daily briefing', icon: 'MessagesSquare' },
  { id: 'activity', label: 'Platform activity', icon: 'Workflow' },
  { id: 'access', label: 'Access management', icon: 'Settings' },
  { id: 'knowledge', label: 'SOP library', icon: 'Pencil' },
] as const

// These are the modules from the brief, mapped to their primary roles and permissions
export const MODULES: Module[] = [
  {
    name: 'CEO Cockpit',
    href: '/dashboard/ceo',
    icon: 'Monitor',
    permissions: ['pipeline:read', 'agents:configure'],
    children: CEO_COCKPIT_SECTIONS.map((section) => ({
      name: section.label,
      href: `/dashboard/ceo#${section.id}`,
      icon: section.icon,
      permissions: ['pipeline:read', 'agents:configure'],
    })),
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
      { name: 'Platform Alerts', href: '/dashboard/enrollment/alerts', icon: 'Bell', permissions: ['sales:alerts:read'] },
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
    permissions: ['business_support:dashboard:read', 'business_support:contracts:read'],
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
  },
  {
    name: 'Calendar & Tasks',
    href: '/dashboard/calendar',
    icon: 'CalendarDays',
    permissions: ['calendar:read']
  }
]

// Keep role loading in the persistent dashboard shell instead of repeating it per widget.
function usePermissionsState() {
  const [session, setSession] = useState<Session | null>(null)
  const [userRoles, setUserRoles] = useState<string[]>([])
  const [permissions, setPermissions] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const requestVersion = useRef(0)
  const inFlightUserId = useRef<string | null>(null)
  const loadedUserId = useRef<string | null>(null)

  useEffect(() => {
    // Only run in browser environment
    if (typeof window !== 'undefined') {
      let active = true

      const loadRoles = async (session: Session | null) => {
        setSession(session)
        if (!session) {
          requestVersion.current += 1
          inFlightUserId.current = null
          loadedUserId.current = null
          setUserRoles([])
          setIsLoading(false)
          return
        }

        const userId = session.user.id
        if (loadedUserId.current === userId || inFlightUserId.current === userId) return

        const currentRequest = ++requestVersion.current
        inFlightUserId.current = userId
        setUserRoles([])
        setIsLoading(true)

        try {
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${session.access_token}` },
          })
          if (!response.ok) {
            throw new Error(`Unable to load account roles (${response.status})`)
          }
          const data = await response.json()
          if (!Array.isArray(data.roles) || !data.roles.every((role: unknown) => typeof role === 'string')) {
            throw new Error('The account roles response was invalid')
          }
          if (active && requestVersion.current === currentRequest) {
            loadedUserId.current = userId
            setUserRoles(data.roles)
          }
        } catch (error) {
          console.error('Unable to load account roles:', error)
          if (active && requestVersion.current === currentRequest) setUserRoles([])
        } finally {
          if (active && requestVersion.current === currentRequest) {
            inFlightUserId.current = null
            setIsLoading(false)
          }
        }
      }

      supabase.auth.getSession()
        .then(({ data: { session } }) => loadRoles(session))
        .catch((error: unknown) => {
          console.error('Unable to read the authentication session:', error)
          if (active) {
            setUserRoles([])
            setIsLoading(false)
          }
        })

      // Listen for auth changes
      const {
        data: { subscription },
      } = supabase.auth.onAuthStateChange((_event, session) => {
        void loadRoles(session)
      })

      // Cleanup
      return () => {
        active = false
        subscription.unsubscribe()
      }
    }
  }, [])

  // Calculate permissions from userRoles
  // Role to permissions mapping based on the seed data in 0001_init_rbac.sql
  const rolePermissions = {
    ceo:  ['leads:read', 'leads:write', 'pipeline:read', 'sales:leads:assign', 'enrollment:leads:assign', 'sales:alerts:read', 'sales:alerts:manage', 'agents:trigger', 'agents:configure', 'students:read', 'students:write', 'ai:chat', 'assistant:briefing:read', 'assistant:briefing:write', 'assistant:automation:trigger', 'assistant:research:write', 'calendar:read', 'calendar:manage', 'integrations:kajabi:manage', 'marketing:read', 'marketing:write', 'marketing:approve', 'marketing:publish', 'marketing:analytics', 'marketing:configure', 'marketing:research', 'marketing:send', 'marketing:integrations', 'marketing:social:sync', 'marketing:approve_sensitive', 'marketing:seo', 'marketing:social', 'video:read', 'video:upload', 'video:edit', 'video:approve', 'video:publish', 'video:team:read:videographer', 'video:team:read:marketing', 'video:team:read:programs', 'video:team:read:student_success', 'marketing:content:read', 'marketing:content:write', 'design:workspace', 'design:manage', 'design:write', 'design:read_marketing', 'design:read_programs', 'design:review_marketing', 'design:review_programs', 'design:templates', 'design:funnels', 'design:analytics', 'design:publish', 'design:request', 'design:publish_marketing', 'design:publish_programs', 'design:ai', 'design:canva', 'payments:kajabi:read', 'payments:paystack:read', 'payments:verify', 'students:attendance:read', 'students:attendance:write', 'students:assignments:read', 'students:intervention:review', 'students:intervention:approve', 'students:course_access:request', 'students:course_access:grant', 'students:course_access:approve', 'business_support:pilot:read', 'business_support:pilot:write'],
    programs_manager: ['students:read', 'pipeline:read', 'ai:chat', 'design:workspace', 'design:read_programs', 'design:review_programs', 'design:request', 'design:publish_programs', 'business_support:dashboard:read', 'business_support:pilot:read', 'business_support:contracts:read', 'payments:kajabi:read', 'payments:paystack:read', 'students:attendance:read', 'students:assignments:read', 'students:intervention:review', 'students:intervention:approve', 'students:course_access:approve'],
    customer_success: ['students:read', 'ai:chat', 'design:workspace', 'design:read_programs', 'design:request', 'payments:kajabi:read', 'payments:paystack:read', 'students:attendance:read', 'students:attendance:write', 'students:assignments:read', 'students:intervention:review', 'students:course_access:request'],
    business_support: ['ai:chat', 'design:workspace', 'design:read_marketing', 'design:request', 'business_support:dashboard:read', 'business_support:pilot:read', 'business_support:pilot:write', 'business_support:contracts:read', 'payments:kajabi:read', 'payments:paystack:read', 'payments:verify', 'students:course_access:grant'],
    marketing: ['ai:chat', 'calendar:read', 'marketing:read', 'marketing:write', 'marketing:analytics', 'marketing:research', 'marketing:seo', 'marketing:social', 'marketing:social:sync', 'video:read', 'video:upload', 'video:edit', 'video:team:read:marketing', 'marketing:content:read', 'marketing:content:write', 'design:workspace', 'design:read_marketing', 'design:ai', 'design:request'],
    marketing_lead: ['ai:chat', 'calendar:read', 'marketing:read', 'marketing:write', 'marketing:approve', 'marketing:publish', 'marketing:analytics', 'marketing:configure', 'marketing:research', 'marketing:send', 'marketing:integrations', 'marketing:social:sync', 'marketing:seo', 'marketing:social', 'video:read', 'video:upload', 'video:edit', 'video:approve', 'video:publish', 'video:team:read:marketing', 'marketing:content:read', 'marketing:content:write', 'design:workspace', 'design:read_marketing', 'design:ai', 'design:review_marketing', 'design:templates', 'design:funnels', 'design:analytics', 'design:publish', 'design:request', 'design:publish_marketing'],
    videographer: ['ai:chat', 'video:read', 'video:upload', 'video:edit', 'video:approve', 'video:publish', 'video:team:read:videographer', 'marketing:content:read', 'marketing:content:write', 'design:read_marketing', 'design:ai', 'design:canva'],
    graphic_designer: ['ai:chat', 'design:workspace', 'design:manage', 'design:write', 'design:templates', 'design:funnels', 'design:analytics', 'design:request', 'design:ai', 'design:canva'],
    executive_assistant: ['pipeline:read', 'agents:trigger', 'ai:chat', 'calendar:read', 'assistant:briefing:read', 'assistant:briefing:write', 'assistant:automation:trigger', 'assistant:research:write'],
    enrollment: ['leads:read', 'leads:write', 'pipeline:read', 'ai:chat', 'sales:alerts:read', 'sales:alerts:manage'],
    sales: ['leads:read', 'leads:write', 'pipeline:read', 'ai:chat', 'sales:alerts:read', 'sales:alerts:manage'],
    enrollment_lead: ['leads:read', 'leads:write', 'pipeline:read', 'ai:chat', 'enrollment:leads:assign', 'sales:alerts:read', 'sales:alerts:manage'],
    sales_lead: ['leads:read', 'leads:write', 'pipeline:read', 'ai:chat', 'sales:leads:assign', 'sales:alerts:read', 'sales:alerts:manage'],
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
    session,
    permissions,
    userRoles,
    isLoading,
    can,
    canAll,
    canAny
  }
}

type PermissionsContextValue = ReturnType<typeof usePermissionsState>
const PermissionsContext = createContext<PermissionsContextValue | null>(null)

export function PermissionsProvider({ children }: { children: ReactNode }) {
  const value = usePermissionsState()
  return createElement(PermissionsContext.Provider, { value, children })
}

export function usePermissions() {
  const context = useContext(PermissionsContext)
  if (!context) {
    throw new Error('usePermissions must be used within a PermissionsProvider')
  }
  return context
}