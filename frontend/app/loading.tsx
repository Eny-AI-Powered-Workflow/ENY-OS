// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/loading.tsx
export default function Loading() {
  return (
    <main role="status" aria-live="polite" className="flex min-h-screen items-center justify-center bg-[#142238] px-6 text-white">
      <div className="flex flex-col items-center text-center">
        <span className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-[#e2b75e] text-sm font-bold text-[#142238]">ENY</span>
        <span aria-hidden="true" className="h-6 w-6 animate-spin rounded-full border-2 border-white/30 border-t-[#e2b75e]" />
        <p className="mt-4 text-sm text-slate-200">Loading ENY OS…</p>
      </div>
    </main>
  )
}
