// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/Sidebar.tsx
import Link from 'next/link'
import { usePermissions } from '@/lib/permissions'
import { MODULES } from '@/lib/permissions'
import { AccessBadge } from '@/components/AccessBadge'
import {
  Monitor, Users, GraduationCap, Megaphone, Settings, Pencil,
  UsersDashboard, LayoutDashboard, ClipboardList, MessagesSquare,
  BarChart3, LogOut
} from 'lucide-react'

export function Sidebar() {
  const { canAll } = usePermissions()

  // Icon mapping
  const iconMap: Record<string, any> = {
    'Monitor': Monitor,
    'Users': Users,
    'GraduationCap': GraduationCap,
    'Megaphone': Megaphone,
    'Settings': Settings,
    'Pencil': Pencil,
    'UsersDashboard': UsersDashboard,
    'LayoutDashboard': LayoutDashboard,
    'ClipboardList': ClipboardList,
    'MessagesSquare': MessagesSquare,
    'BarChart3': BarChart3,
    'LogOut': LogOut
  }

  // Filter modules based on user permissions
  const accessibleModules = MODULES.filter(module =>
    module.permissions.length === 0 || canAll(module.permissions)
  )

  return (
    <aside className="w-64 border-r bg-background">
      <div className="flex-shrink-0 flex items-center px-4 py-6 border-b">
        <h1 className="text-xl font-semibold text-foreground">ENY Platform</h1>
      </div>
      <nav className="mt-4 space-y-1 px-2">
        {accessibleModules.map((module) => {
          const Icon = iconMap[module.icon] || UsersDashboard
          return (
            <Link
              key={module.name}
              href={module.href}
              className={`flex w-items-center px-3 py-2 text-sm font-medium
                        ${window.location.pathname === module.href
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="ml-3">{module.name}</span>
            </Link>
          )
        })}
      </nav>
      <div className="mt-auto pb-4">
        <Link href="/login" className="block w-full text-left px-4 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground">
          <LogOut className="h-4 w-4 mr-3" />
          Sign out
        </Link>
        <div className="px-4 pt-2">
          <AccessBadge />
        </div>
      </div>
    </aside>
  )
}