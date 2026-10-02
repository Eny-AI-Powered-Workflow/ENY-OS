// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/StudentPayments.tsx
'use client'

import { useEffect, useState } from 'react'
import { API_TIMEOUTS, describeHttpError, fetchWithTimeout } from '@/lib/api'
import { usePermissions } from '@/lib/permissions'
import { supabase } from '@/lib/supabaseClient'

type Provider = 'kajabi' | 'paystack'
type PaymentRecord = {
  transaction_id: string | null
  customer_id: string | null
  provider: Provider
  amount_minor: number | null
  currency: string
  status: string
  action: string | null
  transaction_date: string | null
  reference: string | null
  customer_name: string | null
  customer_email: string | null
}
type PaymentVerification = {
  reference: string
  verification_status: 'verified' | 'not_confirmed'
  provider_status: string
  reviewer_id: string
  created_at: string | null
}
type StudentPaymentsProps = {
  enableVerification?: boolean
}
type ProviderState = {
  records: PaymentRecord[]
  page: number
  hasMore: boolean
  loading: boolean
  message: string | null
}

const initialProviderState: ProviderState = {
  records: [],
  page: 0,
  hasMore: false,
  loading: true,
  message: null,
}

async function loadPaymentVerifications(references: string[], accessToken?: string): Promise<Record<string, PaymentVerification>> {
  if (references.length === 0) return {}
  const params = new URLSearchParams()
  references.forEach((reference) => params.append('references', reference))
  const response = await fetchWithTimeout(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/business-support/payments/verification-status?${params}`,
    {
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      credentials: 'include',
    },
    API_TIMEOUTS.standard,
  )
  if (!response.ok) throw new Error(await describeHttpError(response, 'Payment verification history is unavailable.'))
  const payload = await response.json() as { verifications: Record<string, PaymentVerification> }
  return payload.verifications ?? {}
}

function formatAmount(record: PaymentRecord) {
  if (record.amount_minor === null) return 'Unavailable'
  const value = record.amount_minor / 100
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: record.currency,
    }).format(value)
  } catch {
    return `${record.currency} ${value.toFixed(2)}`
  }
}

function formatDate(value: string | null) {
  if (!value) return 'Date unavailable'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleString()
}

export default function StudentPayments({ enableVerification = false }: StudentPaymentsProps) {
  const { can } = usePermissions()
  const canVerify = enableVerification && can('payments:verify')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [appliedRange, setAppliedRange] = useState({ from: '', to: '' })
  const [providers, setProviders] = useState<Record<Provider, ProviderState>>({
    kajabi: initialProviderState,
    paystack: initialProviderState,
  })
  const [verifications, setVerifications] = useState<Record<string, PaymentVerification>>({})
  const [verificationErrors, setVerificationErrors] = useState<Record<string, string>>({})
  const [verifyingReferences, setVerifyingReferences] = useState<string[]>([])
  const [retryKeys, setRetryKeys] = useState<Record<string, string>>({})

  useEffect(() => {
    let cancelled = false

    async function load(provider: Provider, page: number, append: boolean) {
      setProviders((current) => ({
        ...current,
        [provider]: { ...current[provider], loading: true, message: null },
      }))
      try {
        const { data: { session } } = await supabase.auth.getSession()
        const params = new URLSearchParams({ page: String(page), per_page: '25' })
        if (appliedRange.from) params.set('from_date', appliedRange.from)
        if (appliedRange.to) params.set('to_date', appliedRange.to)
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/payments/${provider}?${params}`,
          {
            headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
            credentials: 'include',
          },
        )
        const payload = await response.json()
        if (!response.ok) {
          const code = payload?.detail?.code
          const message = response.status === 403
            ? 'Permission not granted'
            : code === 'provider_not_configured'
              ? 'Provider connection is not configured'
              : 'Payment data is unavailable'
          throw new Error(message)
        }
        if (cancelled) return
        setProviders((current) => ({
          ...current,
          [provider]: {
            records: append ? [...current[provider].records, ...(payload.records ?? [])] : (payload.records ?? []),
            page: payload.page ?? page,
            hasMore: Boolean(payload.has_more),
            loading: false,
            message: null,
          },
        }))
        if (provider === 'paystack' && canVerify) {
          try {
            const statuses = await loadPaymentVerifications(
              (payload.records ?? []).map((record: PaymentRecord) => record.reference).filter((reference: string | null): reference is string => Boolean(reference)),
              session?.access_token,
            )
            if (!cancelled) setVerifications((current) => ({ ...current, ...statuses }))
          } catch {
            if (!cancelled) setVerificationErrors((current) => ({ ...current, _list: 'Verification history is unavailable.' }))
          }
        }
      } catch (error) {
        if (cancelled) return
        setProviders((current) => ({
          ...current,
          [provider]: {
            ...current[provider],
            loading: false,
            message: error instanceof Error ? error.message : 'Payment data is unavailable',
          },
        }))
      }
    }

    setProviders({
      kajabi: { ...initialProviderState, records: [], page: 0 },
      paystack: { ...initialProviderState, records: [], page: 0 },
    })
    void load('kajabi', 1, false)
    void load('paystack', 1, false)

    return () => {
      cancelled = true
    }
  }, [appliedRange, canVerify])

  async function confirmPaystackPayment(reference: string) {
    if (!canVerify) return
    setVerifyingReferences((current) => [...current, reference])
    setVerificationErrors((current) => ({ ...current, [reference]: '' }))
    const idempotencyKey = retryKeys[reference] ?? crypto.randomUUID()
    setRetryKeys((current) => ({ ...current, [reference]: idempotencyKey }))
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetchWithTimeout(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/business-support/payments/verify`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
          },
          credentials: 'include',
          body: JSON.stringify({ reference, idempotency_key: idempotencyKey }),
        },
        API_TIMEOUTS.standard,
      )
      if (!response.ok) throw new Error(await describeHttpError(response, 'Paystack could not confirm this payment.'))
      const payload = await response.json() as { verification: PaymentVerification }
      setVerifications((current) => ({ ...current, [reference]: payload.verification }))
      setRetryKeys((current) => {
        const next = { ...current }
        delete next[reference]
        return next
      })
    } catch (error) {
      setVerificationErrors((current) => ({
        ...current,
        [reference]: error instanceof Error ? error.message : 'Paystack could not confirm this payment.',
      }))
    } finally {
      setVerifyingReferences((current) => current.filter((item) => item !== reference))
    }
  }

  function renderProvider(provider: Provider, title: string, note: string) {
    const state = providers[provider]
    return (
      <section className="min-w-0 border-t border-slate-200 pt-4" aria-labelledby={`${provider}-payments-title`}>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 id={`${provider}-payments-title`} className="text-base font-semibold text-slate-900">{title}</h3>
          <p className="text-xs text-slate-600">{note}</p>
        </div>
        {state.loading && state.records.length === 0 ? (
          <p className="py-6 text-sm text-slate-600">Loading provider records...</p>
        ) : state.message ? (
          <p role="status" className="py-6 text-sm text-slate-700">{state.message}</p>
        ) : state.records.length === 0 ? (
          <p className="py-6 text-sm text-slate-600">No provider records in this date range.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className={`w-full ${canVerify ? 'min-w-[920px]' : 'min-w-[760px]'} border-collapse text-left text-sm`}>
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                  <th className="py-2 pr-4 font-medium">Date</th>
                  <th className="py-2 pr-4 font-medium">Customer</th>
                  <th className="py-2 pr-4 font-medium">Reference</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 text-right font-medium">Amount</th>
                  {canVerify && <th className="py-2 pl-4 font-medium">Payment review</th>}
                </tr>
              </thead>
              <tbody>
                {state.records.map((record) => (
                  <tr key={`${provider}-${record.transaction_id ?? record.reference}`} className="border-b border-slate-100">
                    <td className="py-3 pr-4 text-slate-700">{formatDate(record.transaction_date)}</td>
                    <td className="py-3 pr-4 text-slate-800">
                      <span className="block">{record.customer_name || (record.customer_id ? `Customer ${record.customer_id}` : 'Name unavailable')}</span>
                      <span className="block text-xs text-slate-500">{record.customer_email || 'Email unavailable'}</span>
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs text-slate-600">{record.reference || record.transaction_id || 'Unavailable'}</td>
                    <td className="py-3 pr-4 text-slate-700">
                      <span>{record.status}</span>
                      {record.action && <span className="ml-2 text-xs text-slate-500">{record.action}</span>}
                    </td>
                    <td className="py-3 text-right font-medium text-slate-900">{formatAmount(record)} <span className="text-xs text-slate-500">{record.currency}</span></td>
                    {canVerify && (
                      <td className="py-3 pl-4 text-xs text-slate-700">
                        {provider === 'paystack' && record.reference ? (
                          <div className="grid justify-items-start gap-1">
                            <span>
                              {verifications[record.reference]
                                ? `${verifications[record.reference].verification_status === 'verified' ? 'Confirmed paid' : 'Not confirmed'} by Paystack (${verifications[record.reference].provider_status})`
                                : 'Not yet verified'}
                            </span>
                            {verifications[record.reference]?.created_at && (
                              <span className="text-[11px] text-slate-500">
                                Reviewed {formatDate(verifications[record.reference].created_at)}
                              </span>
                            )}
                            <button
                              type="button"
                              disabled={verifyingReferences.includes(record.reference)}
                              onClick={() => void confirmPaystackPayment(record.reference as string)}
                              className="border border-emerald-700 px-2 py-1 text-xs font-medium text-emerald-900 disabled:opacity-50"
                            >
                              {verifyingReferences.includes(record.reference) ? 'Checking...' : 'Confirm with Paystack'}
                            </button>
                            {verificationErrors[record.reference] && <span role="alert" className="max-w-48 text-rose-700">{verificationErrors[record.reference]}</span>}
                          </div>
                        ) : provider === 'kajabi' ? 'Kajabi remains read-only' : 'Provider reference unavailable'}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {state.hasMore && !state.message && (
          <button
            type="button"
            disabled={state.loading}
            onClick={() => {
              setProviders((current) => ({
                ...current,
                [provider]: { ...current[provider], loading: true },
              }))
              const nextPage = state.page + 1
              const params = new URLSearchParams({ page: String(nextPage), per_page: '25' })
              if (appliedRange.from) params.set('from_date', appliedRange.from)
              if (appliedRange.to) params.set('to_date', appliedRange.to)
              void supabase.auth.getSession().then(async ({ data: { session } }) => {
                const response = await fetch(
                  `${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/payments/${provider}?${params}`,
                  { headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}, credentials: 'include' },
                )
                const payload = await response.json()
                if (!response.ok) throw new Error('Payment data is unavailable')
                setProviders((current) => ({
                  ...current,
                  [provider]: {
                    records: [...current[provider].records, ...(payload.records ?? [])],
                    page: payload.page ?? nextPage,
                    hasMore: Boolean(payload.has_more),
                    loading: false,
                    message: null,
                  },
                }))
                if (provider === 'paystack' && canVerify) {
                  const statuses = await loadPaymentVerifications(
                    (payload.records ?? []).map((record: PaymentRecord) => record.reference).filter((reference: string | null): reference is string => Boolean(reference)),
                    session?.access_token,
                  )
                  setVerifications((current) => ({ ...current, ...statuses }))
                }
              }).catch(() => setProviders((current) => ({
                ...current,
                [provider]: { ...current[provider], loading: false, message: 'Payment data is unavailable' },
              })))
            }}
            className="mt-3 border border-slate-300 px-3 py-2 text-sm text-slate-700 disabled:opacity-50"
          >
            {state.loading ? 'Loading...' : 'Load more'}
          </button>
        )}
      </section>
    )
  }

  function applyDateRange(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAppliedRange({ from: fromDate, to: toDate })
  }

  return (
    <section className="space-y-4 border-y border-slate-300 py-5" aria-labelledby="student-payments-title">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 id="student-payments-title" className="text-lg font-semibold text-slate-900">Payment records</h2>
          <p className="mt-1 text-sm text-slate-600">Provider-reported records only. Business Support remains responsible for payment verification.</p>
        </div>
        <form onSubmit={applyDateRange} className="flex flex-wrap items-end gap-2">
          <label className="grid gap-1 text-xs text-slate-600">
            From
            <input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} className="h-9 border border-slate-300 bg-white px-2 text-sm text-slate-900" />
          </label>
          <label className="grid gap-1 text-xs text-slate-600">
            To
            <input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} className="h-9 border border-slate-300 bg-white px-2 text-sm text-slate-900" />
          </label>
          <button type="submit" className="h-9 border border-slate-700 bg-slate-900 px-3 text-sm text-white">Apply</button>
        </form>
      </div>
      {renderProvider('kajabi', 'Kajabi transactions', 'Original provider currency shown; USD expected.')}
      {renderProvider('paystack', 'Paystack transactions', 'Only NGN transactions shown; amounts are not combined.')}
    </section>
  )
}
