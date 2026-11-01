import SalesOperationsPanel from '@/components/SalesOperationsPanel'

export default function LeadOperationsPage() {
  return (
    <div className="relative -mx-4 -my-6 min-h-full overflow-hidden bg-[#070a10] px-4 pb-10 pt-5 text-slate-100 sm:-mx-6 sm:px-6 sm:pt-6 lg:-mx-8 lg:px-8">
      <div className="pointer-events-none absolute -top-36 left-1/3 h-80 w-[42rem] rounded-full bg-cyan-400/[0.045] blur-3xl" />
      <div className="relative mx-auto w-full max-w-[1720px] space-y-5">
        <header className="flex flex-col justify-between gap-4 border-b border-slate-800 pb-5 md:flex-row md:items-end">
          <div className="min-w-0">
            <p className="inline-flex items-center gap-2 rounded border border-cyan-500/20 bg-cyan-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-widest text-cyan-300">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
              Sales control surface
            </p>
            <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-white sm:text-3xl">Lead Operations Engine</h1>
            <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400 sm:text-sm">
              Unified pipeline monitoring for assignment queues, SLA response windows, routing status, and operator actions.
            </p>
          </div>
          <p className="flex shrink-0 items-center gap-2 self-start rounded-full border border-emerald-500/20 bg-emerald-500/[0.08] px-3 py-1.5 text-[11px] font-medium text-emerald-300 md:self-auto">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-50" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            Live operations
          </p>
        </header>
        <SalesOperationsPanel />
      </div>
    </div>
  )
}
