// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/layout.tsx
import { Sidebar } from '@/components/Sidebar'
import type { ReactNode } from 'react'

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-[#050816] text-white">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="border-b border-white/10 bg-[#0b1020]/90 backdrop-blur-xl">
          <div className="flex items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
            <div>
              <p className="text-[10px] uppercase tracking-[0.22em] text-violet-200/80">Overview</p>
              <h1 className="mt-1 text-xl font-bold text-white">Dashboard</h1>
            </div>
            <div className="hidden items-center gap-3 md:flex">
              <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
                Live operations
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  )
}