import BatchExecutionLedger from '@/components/BatchExecutionLedger'

export default function ApprovedWorkPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <p className="text-[10px] uppercase tracking-[0.24em] text-sky-600">Scoring history</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Approved Work</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Review approved scoring batches, outcomes, failures, and available retries.</p>
      </header>
      <BatchExecutionLedger />
    </div>
  )
}
