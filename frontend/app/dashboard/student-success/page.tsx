// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/student-success/page.tsx
'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  ArrowDown,
  BookOpenCheck,
  CircleDollarSign,
  GraduationCap,
  RefreshCw,
  UsersRound,
} from 'lucide-react'
import StudentSuccessMetrics from '@/components/StudentSuccessMetrics'
import StudentList from '@/components/StudentList'
import StudentProgress from '@/components/StudentProgress'
import StudentPayments from '@/components/StudentPayments'
import StudentLifecycleQueue from '@/components/StudentLifecycleQueue'
import KajabiConnectionSettings from '@/components/KajabiConnectionSettings'
import { API_TIMEOUTS, describeHttpError, fetchWithTimeout, getProviderErrorMessage } from '@/lib/api'
import { usePermissions } from '@/lib/permissions'
import { supabase } from '@/lib/supabaseClient'

type KajabiOffer = { id: string; title: string; currency: string }

export default function StudentSuccessDashboard() {
  const { can } = usePermissions()
  const canManageKajabi = can('integrations:kajabi:manage')
  const [offers, setOffers] = useState<KajabiOffer[]>([])
  const [selectedOfferId, setSelectedOfferId] = useState('')
  const [loadingOffers, setLoadingOffers] = useState(true)
  const [offerError, setOfferError] = useState<string | null>(null)

  const loadOffers = useCallback(async () => {
    setLoadingOffers(true)
    setOfferError(null)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetchWithTimeout(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/offers?page=1&per_page=100`,
        {
          headers: session?.access_token
            ? { Authorization: `Bearer ${session.access_token}` }
            : {},
          credentials: 'include',
          cache: 'no-store',
        },
        API_TIMEOUTS.standard,
      )
      if (!response.ok) {
        if (response.status === 401) throw new Error('Your session has expired. Please log in again.')
        if (response.status === 403) throw new Error('You do not have permission to view Kajabi offers.')
        const providerError = getProviderErrorMessage(await response.json().catch(() => ({})), 'kajabi')
        if (providerError) throw new Error(providerError)
        throw new Error(await describeHttpError(response, 'Kajabi offers are unavailable.'))
      }
      const payload = await response.json() as { offers?: KajabiOffer[] }
      const availableOffers = payload.offers ?? []
      setOffers(availableOffers)
      setSelectedOfferId((current) => availableOffers.some((offer) => offer.id === current)
        ? current
        : availableOffers[0]?.id ?? '')
    } catch (error) {
      setOfferError(error instanceof Error ? error.message : 'Kajabi offers are unavailable.')
    } finally {
      setLoadingOffers(false)
    }
  }, [])

  useEffect(() => {
    void loadOffers()
  }, [loadOffers])

  const selectedOffer = offers.find((offer) => offer.id === selectedOfferId)

  return (
    <main className="space-y-7 pb-10">
      <header className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 px-6 py-7 text-white shadow-lg sm:px-8 sm:py-9">
        <div className="pointer-events-none absolute -right-10 -top-20 h-72 w-72 rounded-full bg-indigo-400/10 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 right-1/3 h-40 w-40 rounded-full bg-cyan-300/10 blur-3xl" />
        <div className="relative flex flex-col gap-7 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-2xl">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-indigo-200">
              <GraduationCap className="h-4 w-4" />
              Student Success · Operations
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">Learner success, at a glance.</h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300">
              Review active enrollment, learner progress and service workflows across the connected student sources.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <SourceBadge icon={<UsersRound className="h-3.5 w-3.5" />} label="Roster · Kajabi" />
              <SourceBadge icon={<BookOpenCheck className="h-3.5 w-3.5" />} label="Learning progress · Program Sheet" />
              <SourceBadge icon={<CircleDollarSign className="h-3.5 w-3.5" />} label="Payments · Kajabi / Paystack" />
            </div>
          </div>

          <div className="w-full rounded-2xl border border-white/15 bg-white/[0.07] p-4 backdrop-blur-sm xl:max-w-sm">
            <div className="flex items-center justify-between gap-3">
              <label htmlFor="active-offer" className="text-xs font-semibold uppercase tracking-wide text-slate-300">
                Active offer
              </label>
              <button
                type="button"
                onClick={() => void loadOffers()}
                disabled={loadingOffers}
                aria-label="Refresh Kajabi offers"
                className="rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${loadingOffers ? 'animate-spin' : ''}`} />
              </button>
            </div>
            {loadingOffers ? (
              <div className="mt-3 h-11 animate-pulse rounded-lg bg-white/10" />
            ) : offers.length > 0 ? (
              <select
                id="active-offer"
                value={selectedOfferId}
                onChange={(event) => setSelectedOfferId(event.target.value)}
                className="mt-2 h-11 w-full rounded-lg border border-white/15 bg-slate-900 px-3 text-sm font-medium text-white outline-none ring-indigo-400 focus:ring-2"
              >
                {offers.map((offer) => <option key={offer.id} value={offer.id}>{offer.title}</option>)}
              </select>
            ) : (
              <div role={offerError ? 'alert' : 'status'} className="mt-3 rounded-lg border border-white/10 bg-white/5 p-3">
                <p className="text-sm text-slate-200">{offerError || 'No active Kajabi offers were returned.'}</p>
                <button type="button" onClick={() => void loadOffers()} className="mt-2 text-xs font-semibold text-indigo-200 hover:text-white">
                  Retry offer connection
                </button>
              </div>
            )}
            {selectedOffer && (
              <p className="mt-2 text-xs text-slate-400">
                Reporting on <span className="font-medium text-slate-200">{selectedOffer.title}</span>
              </p>
            )}
          </div>
        </div>
        <a href="#student-roster" className="relative mt-6 inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-200 hover:text-white">
          Open learner workspace <ArrowDown className="h-3.5 w-3.5" />
        </a>
      </header>

      {canManageKajabi && (
        <details className="group rounded-2xl border border-slate-200 bg-white shadow-sm">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 marker:hidden">
            <span>
              <span className="block text-sm font-semibold text-slate-900">Data connections</span>
              <span className="mt-1 block text-xs text-slate-500">Manage Kajabi credentials and connection status</span>
            </span>
            <span className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 group-open:bg-slate-900 group-open:text-white">
              Configure
            </span>
          </summary>
          <div className="border-t border-slate-100 p-4 sm:p-5">
            <KajabiConnectionSettings />
          </div>
        </details>
      )}

      {selectedOfferId ? (
        <section aria-label="Selected offer overview" className="space-y-3">
          <SectionHeading eyebrow="Enrollment overview" title="The current learner picture" />
          <StudentSuccessMetrics offerId={selectedOfferId} />
        </section>
      ) : (
        <section className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
          <div>
            <h2 className="text-sm font-semibold text-amber-950">Offer data is not available yet</h2>
            <p className="mt-1 text-xs leading-5 text-amber-900">
              The lifecycle playbook and payment records remain available below. Retry Kajabi offers to load learner roster and progress data.
            </p>
          </div>
        </section>
      )}

      <section id="student-roster" className="space-y-3 scroll-mt-6">
        <SectionHeading eyebrow="Learner workspace" title="Students and program progress" />
        {selectedOfferId ? (
          <div className="grid items-start gap-5 xl:grid-cols-[1.12fr_0.88fr]">
            <StudentList offerId={selectedOfferId} />
            <div id="student-progress" className="scroll-mt-6">
              <StudentProgress offerId={selectedOfferId} />
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-8 text-center">
            <UsersRound className="mx-auto h-6 w-6 text-slate-400" />
            <p className="mt-3 text-sm font-semibold text-slate-800">Learner roster is waiting for an active offer</p>
            <p className="mt-1 text-xs text-slate-500">Once Kajabi offers load, select one to see enrolled learners and progress.</p>
          </div>
        )}
      </section>

      <StudentLifecycleQueue />

      <section id="student-payments" className="space-y-3">
        <SectionHeading eyebrow="Revenue operations" title="Provider payment records" />
        <StudentPayments />
      </section>
    </main>
  )
}

function SourceBadge({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] font-medium text-slate-200">
      {icon}
      {label}
    </span>
  )
}

function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-indigo-700">{eyebrow}</p>
      <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950">{title}</h2>
    </div>
  )
}
