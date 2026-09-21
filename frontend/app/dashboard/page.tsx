import Link from 'next/link'
import HotLeadsCard from '@/components/HotLeadsCard'
import DashboardLiveStats from '@/components/DashboardLiveStats'

const modules = [
  { name: 'CEO Cockpit', href: '/dashboard/ceo', code: 'C' },
  { name: 'Sales & Enrollment', href: '/dashboard/enrollment', code: 'S' },
  { name: 'Student Success', href: '/dashboard/student-success', code: 'SS' },
  { name: 'Marketing', href: '/dashboard/marketing', code: 'M' },
  { name: 'Operations', href: '/dashboard/operations', code: 'O' },
  { name: 'Writer & SOPs', href: '/dashboard/writer', code: 'W' },
]

const recentActivity = [
  {
    title: 'Monthly report generated',
    description: 'Sales team completed Q3 forecast analysis',
    time: '2 hours ago',
    icon: '📊',
  },
  {
    title: 'Agent task completed',
    description: 'Enrollment agent processed 150 new applications',
    time: '4 hours ago',
    icon: '🤖',
  },
]

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="rounded-[28px] border border-slate-800 bg-[radial-gradient(circle_at_top_left,_rgba(124,58,237,0.18),_transparent_28%),linear-gradient(135deg,_rgba(15,23,42,0.96),_rgba(14,116,144,0.14),_rgba(15,23,42,0.98))] p-6 shadow-[0_24px_60px_rgba(15,23,42,0.45)] sm:p-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-violet-200">Performance</p>
            <h1 className="mt-3 text-3xl font-black tracking-[-0.05em] text-white sm:text-4xl">
              Welcome back to ENY.
            </h1>
          </div>

          <div className="rounded-full border border-violet-400/30 bg-violet-500/10 px-3 py-1.5 text-xs font-medium text-violet-100">Connected workspaces</div>
        </div>

        <p className="mt-4 max-w-2xl text-base text-slate-300">
          Your unified AI-powered platform for enterprise transformation, growth, and day-to-day execution.
        </p>
      </div>

      <DashboardLiveStats />

      <HotLeadsCard />

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold tracking-[-0.04em] text-white">Quick access</h2>
          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Modules</span>
        </div>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {modules.map((module) => (
            <Link key={module.name} href={module.href} className="group block">
              <div className="h-full rounded-3xl border border-slate-800 bg-slate-900/70 p-5 shadow-[0_14px_30px_rgba(15,23,42,0.2)] transition hover:-translate-y-1 hover:border-violet-400/40 hover:bg-slate-900">
                <div className="mb-5 flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-500/10 text-sm font-bold text-violet-200">
                    {module.code}
                  </div>
                  <span className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Open</span>
                </div>
                <h3 className="text-xl font-semibold text-white">{module.name}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-300">
                  Access the tools, insight layers, and automation workflows built for this department.
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>

    </div>
  )
}