// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/loading.tsx
export default function DashboardLoading() {
  return (
    <div role="status" aria-busy="true" className="min-h-[65vh] space-y-8">
      <span className="sr-only">Loading workspace</span>
      <section aria-hidden="true" className="animate-pulse">
        <div className="h-3 w-36 rounded bg-slate-700" />
        <div className="mt-4 h-8 w-64 max-w-full rounded bg-slate-800" />
        <div className="mt-3 h-4 max-w-xl rounded bg-slate-800/80" />
      </section>

      <section aria-hidden="true" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="min-h-40 animate-pulse rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="h-3 w-2/3 rounded bg-slate-800" />
            <div className="mt-6 h-8 w-1/2 rounded bg-slate-800" />
            <div className="mt-8 h-3 rounded bg-slate-800/80" />
          </div>
        ))}
      </section>

      <section aria-hidden="true" className="grid gap-4 lg:grid-cols-2">
        {[0, 1].map((item) => (
          <div key={item} className="min-h-72 animate-pulse rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="h-5 w-40 rounded bg-slate-800" />
            <div className="mt-6 space-y-4">
              <div className="h-12 rounded-lg bg-slate-800/80" />
              <div className="h-12 rounded-lg bg-slate-800/80" />
              <div className="h-12 rounded-lg bg-slate-800/80" />
            </div>
          </div>
        ))}
      </section>
    </div>
  )
}
