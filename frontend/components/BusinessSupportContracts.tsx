// C:\Users\Melody\Documents\ENY-OS\frontend\components\BusinessSupportContracts.tsx
'use client'

import { useEffect, useState } from 'react'
import { API_TIMEOUTS, describeHttpError, fetchWithTimeout } from '@/lib/api'
import { supabase } from '@/lib/supabaseClient'

type Contract = {
  id: string
  title: string
  status: string
  created_at: string | null
  updated_at: string | null
  type: string
}
type ContractPage = {
  documents: Contract[]
  has_more: boolean
}

export default function BusinessSupportContracts() {
  const [contracts, setContracts] = useState<Contract[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadContracts(requestedPage: number, append: boolean) {
    const { data: { session } } = await supabase.auth.getSession()
    const response = await fetchWithTimeout(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/business-support/contracts/signaturely?page=${requestedPage}&limit=25`,
      {
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        credentials: 'include',
      },
      API_TIMEOUTS.standard,
    )
    if (!response.ok) throw new Error(await describeHttpError(response, 'Signaturely contract status is unavailable.'))
    const payload = await response.json() as ContractPage
    setContracts((current) => append ? [...current, ...(payload.documents ?? [])] : (payload.documents ?? []))
    setHasMore(Boolean(payload.has_more))
    setPage(requestedPage)
  }

  useEffect(() => {
    let active = true
    void loadContracts(1, false)
      .catch((loadError) => {
        if (active) setError(loadError instanceof Error ? loadError.message : 'Signaturely contract status is unavailable.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  async function loadMore() {
    setLoadingMore(true)
    setError(null)
    try {
      await loadContracts(page + 1, true)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Signaturely contract status is unavailable.')
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <section className="space-y-4 border-y border-slate-700 py-5" aria-labelledby="signaturely-contracts-title">
      <div>
        <h2 id="signaturely-contracts-title" className="text-lg font-semibold text-white">Contract status</h2>
        <p className="mt-1 text-sm text-slate-300">Read-only status from Signaturely. Sending and changing contracts remain in the approved provider workflow.</p>
      </div>
      {loading ? <p role="status" className="text-sm text-slate-300">Loading Signaturely documents...</p> : error ? (
        <p role="alert" className="border-l-2 border-rose-400 py-2 pl-3 text-sm text-rose-200">{error}</p>
      ) : contracts.length === 0 ? (
        <p className="text-sm text-slate-300">No Signaturely documents were returned.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-xs uppercase text-slate-400">
                <th className="py-2 pr-4 font-medium">Document</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                <th className="py-2 pr-4 font-medium">Type</th>
                <th className="py-2 font-medium">Updated</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((contract) => (
                <tr key={contract.id} className="border-b border-slate-800 text-slate-200">
                  <td className="py-3 pr-4">{contract.title}</td>
                  <td className="py-3 pr-4">{contract.status}</td>
                  <td className="py-3 pr-4">{contract.type}</td>
                  <td className="py-3">{contract.updated_at ? new Date(contract.updated_at).toLocaleString() : 'Unavailable'}</td>
                </tr>
              ))}
            </tbody>
            </table>
          </div>
          {hasMore && (
            <button type="button" disabled={loadingMore} onClick={() => void loadMore()} className="border border-slate-600 px-3 py-2 text-sm text-slate-200 disabled:opacity-50">
              {loadingMore ? 'Loading...' : 'Load more contracts'}
            </button>
          )}
        </>
      )}
    </section>
  )
}