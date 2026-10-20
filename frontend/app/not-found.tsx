// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/not-found.tsx
import Link from 'next/link'
import { ArrowLeft, ArrowUpRight } from 'lucide-react'

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#142238] px-5 py-16 text-white">
      <div className="w-full max-w-xl">
        <p className="text-sm font-semibold text-[#f0ca79]">ENY OS · Internal platform</p>
        <p className="mt-10 font-serif text-7xl tracking-tight text-white">404</p>
        <h1 className="mt-4 text-2xl font-semibold">We can’t find that page.</h1>
        <p className="mt-3 text-base leading-7 text-slate-300">
          The address may have changed, or this page may not be part of your workspace.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link href="/" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#e2b75e] px-4 text-sm font-semibold text-[#142238] hover:bg-[#f0ca79]">
            <ArrowLeft aria-hidden="true" className="h-4 w-4" /> ENY OS home
          </Link>
          <Link href="/login" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-white/25 px-4 text-sm font-semibold hover:bg-white/5">
            Sign in <ArrowUpRight aria-hidden="true" className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </main>
  )
}
