// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/Sidebar.tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { AccessBadge } from '@/components/AccessBadge'
import { usePermissions, MODULES } from '@/lib/permissions'
import { supabase } from '@/lib/supabaseClient'
import {
  BarChart3,
  ClipboardList,
  GraduationCap,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Megaphone,
  MessagesSquare,
  Monitor,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Settings,
  Sparkles,
  Users,
  Workflow,
  ChevronDown,
  ChevronRight,
  Flame,
} from 'lucide-react'

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const [expandedModules, setExpandedModules] = useState<string[]>(['Sales & Enrollment'])
  const { canAll } = usePermissions()
  const pathname = usePathname()
  const router = useRouter()

  const iconMap: Record<string, any> = {
    Monitor,
    Users,
    GraduationCap,
    Megaphone,
    Settings,
    Pencil,
    LayoutDashboard,
    ClipboardList,
    MessagesSquare,
    BarChart3,
    LogOut,
    Sparkles,
    Flame,
    ListChecks,
    Workflow,
  }

  const accessibleModules = MODULES.filter(
    (module) => module.permissions.length === 0 || canAll(module.permissions)
  )

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  return (
    <aside
      className={`relative flex shrink-0 flex-col border-r border-slate-800/90 bg-slate-950/90 text-slate-100 shadow-[inset_-1px_0_0_rgba(148,163,184,0.15)] transition-all duration-300 ${
        collapsed ? 'w-24' : 'w-72'
      }`}
    >
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-4">
        <div className={`flex items-center gap-3 overflow-hidden ${collapsed ? 'w-full justify-center' : ''}`}>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 via-violet-600 to-purple-700 text-sm font-black text-white shadow-[0_0_25px_rgba(168,85,247,0.35)]">
            ENY
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-[0.24em] text-slate-400">Platform</p>
              <h1 className="truncate text-base font-semibold text-white">Dashboard</h1>
            </div>
          )}
        </div>

        <button
          type="button"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          onClick={() => setCollapsed((value) => !value)}
          className="ml-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-700 bg-slate-900/80 text-slate-300 transition hover:border-violet-400/50 hover:bg-violet-500/10 hover:text-white"
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <nav className="space-y-2 px-3 py-4">
        {accessibleModules.map((module) => {
          const Icon = iconMap[module.icon] || LayoutDashboard
          const isActive = pathname === module.href || pathname.startsWith(`${module.href}/`)
          const accessibleChildren = (module.children || []).filter(
            (child) => child.permissions.length === 0 || canAll(child.permissions)
          )
          const isExpanded = expandedModules.includes(module.name) || isActive

          return (
            <div key={module.name}>
              <div className="flex items-center gap-1">
                <Link
                  href={module.href}
                  title={collapsed ? module.name : undefined}
                  className={`group flex min-w-0 flex-1 items-center rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white shadow-[0_10px_25px_rgba(168,85,247,0.25)]'
                      : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                  } ${collapsed ? 'justify-center px-0' : ''}`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span className="ml-3 truncate">{module.name}</span>}
                </Link>
                {!collapsed && accessibleChildren.length > 0 && (
                  <button
                    type="button"
                    aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${module.name}`}
                    onClick={() => setExpandedModules((current) => current.includes(module.name) ? current.filter((name) => name !== module.name) : [...current, module.name])}
                    className="flex h-9 w-8 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white"
                  >
                    {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </button>
                )}
              </div>
              {!collapsed && isExpanded && accessibleChildren.length > 0 && (
                <div className="ml-4 mt-1 space-y-1 border-l border-slate-800 pl-3">
                  {accessibleChildren.map((child) => {
                    const ChildIcon = iconMap[child.icon] || LayoutDashboard
                    const childActive = pathname === child.href
                    return (
                      <Link
                        key={child.name}
                        href={child.href}
                        className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition ${childActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-100'}`}
                      >
                        <ChildIcon className="h-3.5 w-3.5" />
                        <span className="truncate">{child.name}</span>
                      </Link>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </nav>

      <div className="mt-auto border-t border-slate-800 p-3">
        <button
          type="button"
          onClick={handleSignOut}
          className={`mb-4 flex w-full items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2.5 text-sm font-medium text-slate-200 transition hover:border-rose-400/50 hover:bg-rose-500/10 hover:text-white ${
            collapsed ? 'justify-center px-2' : ''
          }`}
        >
          <LogOut className="h-4 w-4" />
          {!collapsed && 'Sign Out'}
        </button>

        {!collapsed && (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3 shadow-inner shadow-slate-950/30">
            <AccessBadge />
          </div>
        )}
      </div>
    </aside>
  )
}