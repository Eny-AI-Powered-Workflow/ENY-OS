import type { ReactNode } from 'react'

const accentStyles = {
  violet: {
    ring: 'border-violet-500/20 bg-violet-500/10 text-violet-200',
    glow: 'from-violet-500/20 via-violet-500/5 to-transparent',
  },
  emerald: {
    ring: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-200',
    glow: 'from-emerald-500/20 via-emerald-500/5 to-transparent',
  },
  amber: {
    ring: 'border-amber-500/20 bg-amber-500/10 text-amber-200',
    glow: 'from-amber-500/20 via-amber-500/5 to-transparent',
  },
  sky: {
    ring: 'border-sky-500/20 bg-sky-500/10 text-sky-200',
    glow: 'from-sky-500/20 via-sky-500/5 to-transparent',
  },
  rose: {
    ring: 'border-rose-500/20 bg-rose-500/10 text-rose-200',
    glow: 'from-rose-500/20 via-rose-500/5 to-transparent',
  },
} as const

type MetricCardProps = {
  title: string
  value: string
  helper?: string
  icon: ReactNode
  accent?: keyof typeof accentStyles
}

export function MetricCard({ title, value, helper, icon, accent = 'violet' }: MetricCardProps) {
  const palette = accentStyles[accent]

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-[0_16px_40px_rgba(15,23,42,0.32)] transition-all duration-200 hover:-translate-y-0.5 hover:border-violet-400/40 hover:bg-slate-900">
      <div className={`absolute inset-x-0 top-0 h-20 bg-gradient-to-br ${palette.glow}`} />
      <div className="relative">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[0.68rem] font-medium uppercase tracking-[0.18em] text-slate-400">{title}</p>
            <p className="mt-3 text-2xl font-bold tracking-[-0.04em] text-white sm:text-[2rem]">{value}</p>
          </div>
          <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border ${palette.ring}`}>
            <span className="text-lg leading-none">{icon}</span>
          </div>
        </div>

        {helper && (
          <div className="mt-4 flex items-center justify-between border-t border-slate-800 pt-3 text-xs text-slate-400">
            <span>{helper}</span>
            <span className="rounded-full border border-slate-700 bg-slate-800/70 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-slate-300">
              Live
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
