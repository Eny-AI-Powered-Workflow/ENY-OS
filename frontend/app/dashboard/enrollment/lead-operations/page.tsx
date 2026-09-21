import SalesOperationsPanel from '@/components/SalesOperationsPanel'

export default function LeadOperationsPage() {
  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <p className="text-[10px] uppercase tracking-[0.24em] text-cyan-600">Sales control room</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Lead Operations</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Sort the working queue by ownership, status, source, score, and next action.</p>
      </header>
      <SalesOperationsPanel />
    </div>
  )
}
