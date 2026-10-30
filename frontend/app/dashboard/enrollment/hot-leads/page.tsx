import HotLeadsCard from '@/components/HotLeadsCard'

export default function HotLeadsPage() {
  return (
    <div className="relative -mx-4 -my-6 min-h-full overflow-hidden bg-[#090d15] px-4 pb-10 pt-5 text-slate-100 sm:-mx-6 sm:px-6 sm:pt-6 lg:-mx-8 lg:px-8">
      <div className="pointer-events-none absolute -top-32 left-1/2 h-72 w-[36rem] -translate-x-1/2 rounded-full bg-amber-400/[0.06] blur-3xl" />
      <div className="relative mx-auto w-full max-w-[1680px] space-y-5">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-300">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              Sales queue <span className="text-slate-600">·</span> ENY-SALES-SCORE
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-100 sm:text-[28px]">Hot Leads</h1>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-400 sm:text-sm">Prioritized leads ready for an owner and a timely first touch.</p>
          </div>
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/[0.08] px-3 py-1.5 text-[11px] font-medium text-emerald-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            Live
          </span>
        </header>
        <HotLeadsCard />
      </div>
    </div>
  )
}
