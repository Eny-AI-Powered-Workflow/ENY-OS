// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/Sidebar.tsx
'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { usePermissions } from '@/lib/permissions'
import { MODULES } from '@/lib/permissions'
import { AccessBadge } from '@/components/AccessBadge'
import { Monitor, Users, GraduationCap, Megaphone, Settings, Pencil, LayoutDashboard, ClipboardList, MessagesSquare, BarChart3, LogOut } from 'lucide-react'
import { usePathname } from 'next/navigation'
import { supabase } from '@/lib/supabaseClient'

export function Sidebar() {
  const { canAll } = usePermissions()
  const pathname = usePathname()
  const router = useRouter()

  const iconMap: Record<string, any> = {
    'Monitor': Monitor,
    'Users': Users,
    'GraduationCap': GraduationCap,
    'Megaphone': Megaphone,
    'Settings': Settings,
    'Pencil': Pencil,
    'LayoutDashboard': LayoutDashboard,
    'ClipboardList': ClipboardList,
    'MessagesSquare': MessagesSquare,
    'BarChart3': BarChart3,
    'LogOut': LogOut
  }

  const accessibleModules = MODULES.filter(module =>
    module.permissions.length === 0 || canAll(module.permissions)
  )

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  return (
    <aside className="w-72 border-r border-white/10 bg-slate-950 text-slate-50 shadow-[inset_-1px_0_0_rgba(255,255,255,0.06)]">
      <div className="flex items-center gap-3 border-b border-white/10 px-5 py-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 text-sm font-bold text-slate-950 shadow-lg shadow-amber-500/20">
          ENY
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-[0.24em] text-slate-400">Platform</p>
          <h1 className="text-lg font-semibold text-white">ENY Dashboard</h1>
        </div>
      </div>

      <nav className="space-y-2 px-3 py-4">
        {accessibleModules.map((module) => {
          const Icon = iconMap[module.icon] || LayoutDashboard
          const isActive = pathname === module.href || pathname.startsWith(`${module.href}/`)

          return (
            <Link
              key={module.name}
              href={module.href}
              className={`group flex items-center rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-amber-400 to-orange-500 text-slate-950 shadow-lg shadow-amber-500/20'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="ml-3">{module.name}</span>
            </Link>
          )
        })}
      </nav>

      <div className="mt-auto border-t border-white/10 p-4">
        <button
          type="button"
          onClick={handleSignOut}
          className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm font-medium text-slate-200 transition hover:border-rose-400/50 hover:bg-rose-500/10 hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 shadow-inner shadow-slate-950/30">
          <AccessBadge />
        </div>
      </div>
    </aside>
  )
}