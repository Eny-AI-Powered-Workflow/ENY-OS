// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/layout.tsx
import { Sidebar } from '@/components/Sidebar'
import type { ReactNode } from 'react'

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-50">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(124,58,237,0.18),_transparent_20%),linear-gradient(180deg,_#020817_0%,_#0f172a_100%)]">
        <header className="border-b border-slate-800/90 bg-slate-950/80 backdrop-blur-xl">
          <div className="flex items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-violet-200/80">Overview</p>
              <h1 className="mt-1 text-xl font-semibold tracking-[-0.04em] text-white">Dashboard</h1>
            </div>
            <div className="hidden items-center gap-3 md:flex">
              <div className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs font-medium text-slate-200 shadow-sm">
                Live operations
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  )
}