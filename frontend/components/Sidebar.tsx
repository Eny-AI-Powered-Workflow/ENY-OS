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
  LogOut,
  Megaphone,
  Menu,
  MessagesSquare,
  Monitor,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Settings,
  Users,
} from 'lucide-react'

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
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
      className={`relative flex shrink-0 flex-col border-r border-white/10 bg-[#0b1020]/95 text-slate-50 shadow-[inset_-1px_0_0_rgba(255,255,255,0.06)] transition-all duration-300 ${
        collapsed ? 'w-24' : 'w-72'
      }`}
    >
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-4">
        <div className={`flex items-center gap-3 overflow-hidden ${collapsed ? 'justify-center w-full' : ''}`}>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-purple-700 text-sm font-black text-white shadow-[0_0_25px_rgba(168,85,247,0.5)]">
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
          className="ml-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-slate-300 transition hover:border-violet-400/50 hover:bg-violet-500/10 hover:text-white"
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <nav className="space-y-2 px-3 py-4">
        {accessibleModules.map((module) => {
          const Icon = iconMap[module.icon] || LayoutDashboard
          const isActive = pathname === module.href || pathname.startsWith(`${module.href}/`)

          return (
            <Link
              key={module.name}
              href={module.href}
              title={collapsed ? module.name : undefined}
              className={`group flex items-center rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white shadow-[0_10px_25px_rgba(168,85,247,0.35)]'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white'
              } ${collapsed ? 'justify-center px-0' : ''}`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="ml-3 truncate">{module.name}</span>}
            </Link>
          )
        })}
      </nav>

      <div className="mt-auto border-t border-white/10 p-3">
        <button
          type="button"
          onClick={handleSignOut}
          className={`mb-4 flex w-full items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm font-medium text-slate-200 transition hover:border-rose-400/50 hover:bg-rose-500/10 hover:text-white ${
            collapsed ? 'justify-center px-2' : ''
          }`}
        >
          <LogOut className="h-4 w-4" />
          {!collapsed && 'Sign Out'}
        </button>

        {!collapsed && (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-3 shadow-inner shadow-slate-950/30">
            <AccessBadge />
          </div>
        )}
      </div>
    </aside>
  )
}