// C:\Users\Melody\Documents\ENY-OS\frontend\components\BusinessSupportPilotReview.tsx
'use client'

import { FormEvent, useEffect, useState } from 'react'
import { API_TIMEOUTS, describeHttpError, fetchWithTimeout } from '@/lib/api'
import { usePermissions } from '@/lib/permissions'
import { supabase } from '@/lib/supabaseClient'

type Scenario = 'shadow_output' | 'provider_unavailable' | 'malformed_or_duplicate_webhook' | 'delayed_payment_evidence' | 'missing_recording' | 'rejected_action'
type Workflow = 'eny-prog-onboard' | 'eny-prog-monitor'
type Result = 'expected' | 'unexpected' | 'not_run'
type Review = {
  id: string
  scenario: Scenario
  workflow_name: Workflow | null
  result: Result
  false_positive: boolean | null
  missing_data: boolean | null
  processing_seconds: number | null
  escalation_quality: number | null
  created_at: string | null
}
type ReviewResponse = {
  summary: {
    total_reviews: number
    expected: number
    unexpected: number
    not_run: number
    false_positive_samples: number
    missing_data_samples: number
    average_processing_seconds: number | null
    average_escalation_quality: number | null
  }
  reviews: Review[]
  truncated: boolean
}

const scenarioLabels: Record<Scenario, string> = {
  shadow_output: 'Shadow workflow output',
  provider_unavailable: 'Provider unavailable',
  malformed_or_duplicate_webhook: 'Malformed or duplicate webhook',
  delayed_payment_evidence: 'Delayed payment evidence',
  missing_recording: 'Missing recording',
  rejected_action: 'Rejected action',
}

const emptySummary: ReviewResponse['summary'] = {
  total_reviews: 0,
  expected: 0,
  unexpected: 0,
  not_run: 0,
  false_positive_samples: 0,
  missing_data_samples: 0,
  average_processing_seconds: null,
  average_escalation_quality: null,
}

async function authHeaders(): Promise<HeadersInit> {
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}
}

export default function BusinessSupportPilotReview() {
  const { can } = usePermissions()
  const canWrite = can('business_support:pilot:write')
  const [data, setData] = useState<ReviewResponse>({ summary: emptySummary, reviews: [], truncated: false })
  const [scenario, setScenario] = useState<Scenario>('shadow_output')
  const [workflow, setWorkflow] = useState<Workflow>('eny-prog-onboard')
  const [result, setResult] = useState<Result>('not_run')
  const [falsePositive, setFalsePositive] = useState(false)
  const [missingData, setMissingData] = useState(false)
  const [processingSeconds, setProcessingSeconds] = useState('')
  const [escalationQuality, setEscalationQuality] = useState('')
  const [submissionId, setSubmissionId] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  async function loadReviews() {
    const response = await fetchWithTimeout(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/business-support/pilot/reviews?days=7`,
      { headers: await authHeaders(), credentials: 'include' },
      API_TIMEOUTS.standard,
    )
    if (!response.ok) throw new Error(await describeHttpError(response, 'Pilot review data is unavailable.'))
    setData(await response.json() as ReviewResponse)
  }

  useEffect(() => {
    let active = true
    setSubmissionId(crypto.randomUUID())
    void loadReviews()
      .catch((loadError) => {
        if (active) setError(loadError instanceof Error ? loadError.message : 'Pilot review data is unavailable.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  async function submitReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!submissionId) return
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const response = await fetchWithTimeout(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/business-support/pilot/reviews`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...await authHeaders() },
          credentials: 'include',
          body: JSON.stringify({
            id: submissionId,
            scenario,
            workflow_name: scenario === 'shadow_output' ? workflow : null,
            result,
            false_positive: falsePositive,
            missing_data: missingData,
            processing_seconds: processingSeconds === '' ? null : Number(processingSeconds),
            escalation_quality: escalationQuality === '' ? null : Number(escalationQuality),
          }),
        },
        API_TIMEOUTS.standard,
      )
      if (!response.ok) throw new Error(await describeHttpError(response, 'Pilot review could not be saved.'))
      setSubmissionId(crypto.randomUUID())
      setMessage('Pilot review recorded.')
      await loadReviews()
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Pilot review could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  const summaryItems = [
    ['Samples', data.summary.total_reviews],
    ['Expected', data.summary.expected],
    ['Unexpected', data.summary.unexpected],
    ['False positives', data.summary.false_positive_samples],
    ['Missing data', data.summary.missing_data_samples],
    ['Avg. seconds', data.summary.average_processing_seconds ?? 'N/A'],
    ['Escalation score', data.summary.average_escalation_quality ?? 'N/A'],
  ] as const

  return (
    <section className="space-y-5 border-y border-slate-700 py-5" aria-labelledby="pilot-review-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="pilot-review-title" className="text-lg font-semibold text-white">Seven-day pilot review</h2>
          <p className="mt-1 text-sm text-slate-300">Record shadow and contingency results. Do not enter student, customer, payment, or provider identifiers.</p>
        </div>
        <span className="border border-amber-700 px-2.5 py-1 text-xs text-amber-200">No external actions</span>
      </div>

      {loading ? <p role="status" className="text-sm text-slate-300">Loading pilot measurements...</p> : (
        <>
          <dl className="grid grid-cols-2 gap-x-5 gap-y-3 border-b border-slate-700 pb-4 sm:grid-cols-4 xl:grid-cols-7">
            {summaryItems.map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs text-slate-400">{label}</dt>
                <dd className="mt-1 text-lg font-semibold text-white">{value}</dd>
              </div>
            ))}
          </dl>

          {canWrite ? <form onSubmit={submitReview} className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="grid gap-1 text-xs text-slate-300">
              Scenario
              <select value={scenario} onChange={(event) => setScenario(event.target.value as Scenario)} className="h-10 border border-slate-600 bg-slate-900 px-3 text-sm text-white">
                {Object.entries(scenarioLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            {scenario === 'shadow_output' && (
              <label className="grid gap-1 text-xs text-slate-300">
                Workflow
                <select value={workflow} onChange={(event) => setWorkflow(event.target.value as Workflow)} className="h-10 border border-slate-600 bg-slate-900 px-3 text-sm text-white">
                  <option value="eny-prog-onboard">ENY-PROG-ONBOARD</option>
                  <option value="eny-prog-monitor">ENY-PROG-MONITOR</option>
                </select>
              </label>
            )}
            <label className="grid gap-1 text-xs text-slate-300">
              Result
              <select value={result} onChange={(event) => setResult(event.target.value as Result)} className="h-10 border border-slate-600 bg-slate-900 px-3 text-sm text-white">
                <option value="not_run">Not run</option>
                <option value="expected">Expected</option>
                <option value="unexpected">Unexpected</option>
              </select>
            </label>
            <label className="grid gap-1 text-xs text-slate-300">
              Processing seconds
              <input type="number" min="0" max="604800" value={processingSeconds} onChange={(event) => setProcessingSeconds(event.target.value)} className="h-10 border border-slate-600 bg-slate-900 px-3 text-sm text-white" />
            </label>
            <label className="grid gap-1 text-xs text-slate-300">
              Escalation quality (1-5)
              <input type="number" min="1" max="5" value={escalationQuality} onChange={(event) => setEscalationQuality(event.target.value)} className="h-10 border border-slate-600 bg-slate-900 px-3 text-sm text-white" />
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-200">
              <input type="checkbox" checked={falsePositive} onChange={(event) => setFalsePositive(event.target.checked)} className="h-4 w-4 accent-rose-500" />
              False positive in sample
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-200">
              <input type="checkbox" checked={missingData} onChange={(event) => setMissingData(event.target.checked)} className="h-4 w-4 accent-amber-400" />
              Required data missing
            </label>
            <div className="flex items-end">
              <button type="submit" disabled={saving || loading || !submissionId} className="h-10 border border-teal-500 bg-teal-700 px-4 text-sm font-medium text-white disabled:opacity-50">
                {saving ? 'Recording...' : 'Record pilot review'}
              </button>
            </div>
          </form> : <p className="text-sm text-slate-300">Read-only pilot review access.</p>}
          {error && <p role="alert" className="border-l-2 border-rose-400 py-2 pl-3 text-sm text-rose-200">{error}</p>}
          {message && <p role="status" className="text-sm text-teal-200">{message}</p>}
          {data.truncated && <p className="text-xs text-slate-400">Showing only the latest 500 reviews; summary reflects those shown.</p>}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-700 text-xs uppercase text-slate-400">
                  <th className="py-2 pr-4 font-medium">Time</th>
                  <th className="py-2 pr-4 font-medium">Scenario</th>
                  <th className="py-2 pr-4 font-medium">Workflow</th>
                  <th className="py-2 pr-4 font-medium">Result</th>
                  <th className="py-2 font-medium">Flags</th>
                </tr>
              </thead>
              <tbody>
                {data.reviews.map((review) => (
                  <tr key={review.id} className="border-b border-slate-800 text-slate-200">
                    <td className="py-3 pr-4">{review.created_at ? new Date(review.created_at).toLocaleString() : 'Time unavailable'}</td>
                    <td className="py-3 pr-4">{scenarioLabels[review.scenario]}</td>
                    <td className="py-3 pr-4">{review.workflow_name ?? 'N/A'}</td>
                    <td className="py-3 pr-4">{review.result.replace('_', ' ')}</td>
                    <td className="py-3">{[review.false_positive && 'false positive', review.missing_data && 'missing data'].filter(Boolean).join(', ') || 'none'}</td>
                  </tr>
                ))}
                {data.reviews.length === 0 && <tr><td colSpan={5} className="py-5 text-slate-400">No pilot reviews recorded in the last seven days.</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}