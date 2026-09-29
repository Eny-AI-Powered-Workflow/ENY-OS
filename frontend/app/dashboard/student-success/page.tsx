'use client'

import { useEffect, useState } from 'react'
import StudentSuccessMetrics from '@/components/StudentSuccessMetrics'
import StudentList from '@/components/StudentList'
import StudentProgress from '@/components/StudentProgress'
import StudentPayments from '@/components/StudentPayments'
import { supabase } from '@/lib/supabaseClient'

type KajabiOffer = { id: string; title: string; currency: string }

export default function StudentSuccessDashboard() {
  const [offers, setOffers] = useState<KajabiOffer[]>([])
  const [selectedOfferId, setSelectedOfferId] = useState('')
  const [loadingOffers, setLoadingOffers] = useState(true)
  const [offerError, setOfferError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    async function loadOffers() {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/offers?page=1&per_page=100`,
          { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' },
        )
        const payload = await response.json()
        if (!response.ok) {
          if (response.status === 401) throw new Error('Your session has expired. Please log in again.')
          if (response.status === 403) throw new Error('You do not have permission to view the Kajabi roster.')
          if (payload?.detail?.code === 'provider_not_configured') throw new Error('Kajabi is not configured in the backend environment.')
          throw new Error('Kajabi offers are unavailable.')
        }
        if (!active) return
        const availableOffers = payload.offers ?? []
        setOffers(availableOffers)
        setSelectedOfferId(availableOffers[0]?.id ?? '')
      } catch (error) {
        if (active) setOfferError(error instanceof Error ? error.message : 'Kajabi offers are unavailable.')
      } finally {
        if (active) setLoadingOffers(false)
      }
    }
    void loadOffers()
    return () => { active = false }
  }, [])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col items-center text-center py-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Student Success
        </h1>
        <p className="text-xl text-muted-foreground max-w-xl">
          Student lifecycle sources and provider-reported payment records
        </p>
      </div>

      <section className="flex flex-col gap-2 border-y border-slate-300 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Kajabi active offer</h2>
          <p className="text-xs text-slate-600">Roster entries are current Kajabi customers granted this offer.</p>
        </div>
        {loadingOffers ? (
          <p className="text-sm text-slate-600">Loading offers...</p>
        ) : offers.length > 0 ? (
          <select value={selectedOfferId} onChange={(event) => setSelectedOfferId(event.target.value)} className="h-10 min-w-64 border border-slate-300 bg-white px-3 text-sm text-slate-900">
            {offers.map((offer) => <option key={offer.id} value={offer.id}>{offer.title}</option>)}
          </select>
        ) : (
          <p role="status" className="text-sm text-slate-700">{offerError || 'No active Kajabi offers are available.'}</p>
        )}
      </section>

      <StudentPayments />

      {selectedOfferId && (
        <>
          <StudentSuccessMetrics offerId={selectedOfferId} />
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <StudentList offerId={selectedOfferId} />
            <StudentProgress offerId={selectedOfferId} />
          </div>
        </>
      )}
    </div>
  );
}