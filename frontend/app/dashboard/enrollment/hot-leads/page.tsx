import HotLeadsCard from '@/components/HotLeadsCard'

export default function HotLeadsPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <p className="text-[10px] uppercase tracking-[0.24em] text-amber-600">Sales queue</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Hot Leads</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Prioritized leads ready for an owner and a timely first touch.</p>
      </header>
      <HotLeadsCard />
    </div>
  )
}
