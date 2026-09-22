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
  value: string | number | null
  helper?: string
  icon: ReactNode
  accent?: keyof typeof accentStyles
}

export function MetricCard({ title, value, helper, icon, accent = 'violet' }: MetricCardProps) {
  const palette = accentStyles[accent]
  const displayValue = value === null || value === undefined ? 'Not tracked' : value

  return (
    <div className="group relative flex h-full min-h-[170px] flex-col overflow-hidden rounded-[24px] border border-slate-800/90 bg-slate-900/80 p-4 shadow-[0_18px_38px_rgba(15,23,42,0.3)] transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-600 hover:bg-slate-900/95 sm:p-5">
      <div className={`absolute inset-x-0 top-0 h-20 bg-gradient-to-br ${palette.glow}`} />

      <div className="relative flex h-full flex-col">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-[0.64rem] font-semibold uppercase tracking-[0.18em] text-slate-400">{title}</p>
            <p className={`mt-3 break-words font-black tracking-[-0.06em] ${displayValue === 'Not tracked' ? 'text-lg text-slate-500' : 'text-2xl text-white sm:text-[2rem]'}`}>
              {displayValue}
            </p>
          </div>

          <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border ${palette.ring}`}>
            <span className="text-base leading-none sm:text-lg">{icon}</span>
          </div>
        </div>

        {helper && (
          <div className="mt-auto flex items-center justify-between gap-2 border-t border-slate-800/90 pt-3 text-[11px] text-slate-400">
            <span className="truncate">{helper}</span>
            <span className="shrink-0 rounded-full border border-slate-700 bg-slate-800/70 px-2 py-1 text-[9px] font-medium uppercase tracking-[0.18em] text-slate-300">
              {displayValue === 'Not tracked' ? 'Pending' : 'Live'}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
