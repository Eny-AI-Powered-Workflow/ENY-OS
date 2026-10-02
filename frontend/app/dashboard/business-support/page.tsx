// C:\Users\Melody\Documents\ENY-OS\frontend\app\dashboard\business-support\page.tsx
'use client'

import { useEffect, useState } from 'react'
import BusinessSupportContracts from '@/components/BusinessSupportContracts'
import BusinessSupportPilotReview from '@/components/BusinessSupportPilotReview'
import StudentPayments from '@/components/StudentPayments'
import { API_TIMEOUTS, describeHttpError, fetchWithTimeout } from '@/lib/api'
import { supabase } from '@/lib/supabaseClient'

type BusinessSupportOverview = {
  department: string
  mode: 'read_only'
  available_views: string[]
  notice: string
}

export default function BusinessSupportDashboard() {
  const [overview, setOverview] = useState<BusinessSupportOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function loadOverview() {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        const response = await fetchWithTimeout(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/business-support/overview`,
          {
            headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
            credentials: 'include',
          },
          API_TIMEOUTS.standard,
        )
        if (!response.ok) {
          throw new Error(await describeHttpError(response, 'Business Support workspace is unavailable.'))
        }
        const payload = await response.json() as BusinessSupportOverview
        if (active) setOverview(payload)
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : 'Business Support workspace is unavailable.')
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadOverview()
    return () => { active = false }
  }, [])

  return (
    <div className="space-y-7">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-700 pb-5">
        <div>
          <p className="text-xs font-medium uppercase text-teal-300">Operations</p>
          <h1 className="mt-2 text-2xl font-semibold text-white">Business Support</h1>
        </div>
        <span className="border border-teal-700 px-2.5 py-1 text-xs font-medium text-teal-200">Read-only pilot</span>
      </header>

      {loading ? (
        <p role="status" className="text-sm text-slate-300">Checking workspace access...</p>
      ) : error ? (
        <p role="alert" className="border-l-2 border-rose-400 py-2 pl-3 text-sm text-rose-200">{error}</p>
      ) : overview ? (
        <>
          <p className="max-w-3xl text-sm text-slate-300">{overview.notice}</p>
          {overview.available_views.includes('payment_records') && <StudentPayments enableVerification />}
          {overview.available_views.includes('contract_status') && <BusinessSupportContracts />}
          <BusinessSupportPilotReview />
        </>
      ) : null}
    </div>
  )
}