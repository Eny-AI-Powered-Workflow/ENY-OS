// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/StudentLifecycleQueue.tsx
'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  ClipboardList,
  Clock3,
  MessageSquareText,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react'
import { API_TIMEOUTS, describeHttpError, fetchWithTimeout } from '@/lib/api'
import { usePermissions } from '@/lib/permissions'
import { supabase } from '@/lib/supabaseClient'

type QueueItem = {
  id: string
  workflow: string
  label: string
  student_name: string
  status: string
  manual_review_required: boolean
  approved_for_send: boolean
  owner: string
  summary: string
  last_updated: string
}

type DraftItem = {
  id: string
  student_name: string
  category: string
  message: string
  status: string
  approved_for_send: boolean
  requires_human_approval: boolean
  owner: string
  last_updated: string
}

type LoadState<T> = {
  items: T[]
  loading: boolean
  error: string | null
}

const initialState = <T,>(): LoadState<T> => ({ items: [], loading: true, error: null })

export default function StudentLifecycleQueue() {
  const { can } = usePermissions()
  const canReadQueue = can('students:read')
  const canReviewDrafts = can('students:intervention:review')
  const [queue, setQueue] = useState<LoadState<QueueItem>>(initialState)
  const [drafts, setDrafts] = useState<LoadState<DraftItem>>(initialState)

  const loadQueue = useCallback(async () => {
    if (!canReadQueue) {
      setQueue({ items: [], loading: false, error: 'Your role does not have access to lifecycle workflows.' })
      return
    }
    setQueue((current) => ({ ...current, loading: true, error: null }))
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetchWithTimeout(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/lifecycle/queue`,
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
        throw new Error(await describeHttpError(response, 'Lifecycle workflow information is unavailable.'))
      }
      const payload = await response.json() as { items?: QueueItem[] }
      setQueue({ items: payload.items ?? [], loading: false, error: null })
    } catch (error) {
      setQueue((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : 'Lifecycle workflow information is unavailable.',
      }))
    }
  }, [canReadQueue])

  const loadDrafts = useCallback(async () => {
    if (!canReviewDrafts) {
      setDrafts({ items: [], loading: false, error: null })
      return
    }
    setDrafts((current) => ({ ...current, loading: true, error: null }))
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetchWithTimeout(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/lifecycle/drafts`,
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
        throw new Error(await describeHttpError(response, 'Communication drafts are unavailable.'))
      }
      const payload = await response.json() as { items?: DraftItem[] }
      setDrafts({ items: payload.items ?? [], loading: false, error: null })
    } catch (error) {
      setDrafts((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : 'Communication drafts are unavailable.',
      }))
    }
  }, [canReviewDrafts])

  useEffect(() => {
    if (canReadQueue) void loadQueue()
    else setQueue({ items: [], loading: false, error: 'Your role does not have access to lifecycle workflows.' })
  }, [canReadQueue, loadQueue])

  useEffect(() => {
    void loadDrafts()
  }, [loadDrafts])

  const manualReviewCount = queue.items.filter((item) => item.manual_review_required).length

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-col gap-4 border-b border-slate-100 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-700">
            <ClipboardList className="h-5 w-5" />
          </span>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-700">Service delivery</p>
            <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">Lifecycle workflows</h2>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-500">
              In-memory examples for onboarding, learner support and graduation—not live student cases. Messages are not sent, and examples may reset when the service restarts.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1.5 text-[11px] font-semibold text-amber-800">
            <ShieldCheck className="h-3.5 w-3.5" />
            Human approval required
          </span>
          <button
            type="button"
            onClick={() => {
              void loadQueue()
              void loadDrafts()
            }}
            disabled={queue.loading || drafts.loading}
            aria-label="Refresh lifecycle workflows"
            className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 hover:text-slate-800 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${queue.loading || drafts.loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      <div className="grid gap-0 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="p-5 sm:p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Workflow playbook</h3>
              <p className="mt-1 text-xs text-slate-500">Safety rails currently available to the team.</p>
            </div>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
              {queue.loading ? 'Loading' : `${queue.items.length} patterns`}
            </span>
          </div>

          {queue.error ? (
            <LoadError message={queue.error} onRetry={() => void loadQueue()} />
          ) : queue.loading ? (
            <div className="grid gap-3 sm:grid-cols-2" aria-label="Loading lifecycle workflows">
              {[0, 1, 2, 3].map((item) => <div key={item} className="h-32 animate-pulse rounded-xl bg-slate-100" />)}
            </div>
          ) : queue.items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-200 px-4 py-8 text-center">
              <p className="text-sm font-medium text-slate-700">No workflow templates available</p>
              <p className="mt-1 text-xs text-slate-500">Try refreshing this section.</p>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {queue.items.map((item, index) => (
                <article key={item.id} className="rounded-xl border border-slate-200 p-4 transition hover:border-violet-200 hover:shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-xs font-semibold text-slate-600">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-semibold capitalize text-amber-800">
                      {item.status.replaceAll('_', ' ')}
                    </span>
                  </div>
                  <h4 className="mt-3 text-sm font-semibold text-slate-900">{item.label}</h4>
                  <p className="mt-1 line-clamp-3 text-xs leading-5 text-slate-600">{item.summary}</p>
                  <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2.5 text-[10px] text-slate-500">
                    <span className="capitalize">{item.owner.replaceAll('_', ' ')}</span>
                    <span className="inline-flex items-center gap-1">
                      <Clock3 className="h-3 w-3" />
                      {item.manual_review_required ? 'Review gate' : 'Draft only'}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          )}

          {!queue.loading && !queue.error && queue.items.length > 0 && (
            <p className="mt-3 text-[11px] text-slate-500">
              {manualReviewCount} of {queue.items.length} workflow patterns require manual review before any action.
            </p>
          )}
        </div>

        <aside className="border-t border-slate-100 bg-slate-50/70 p-5 sm:p-6 xl:border-l xl:border-t-0">
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-sky-700">
              <MessageSquareText className="h-4 w-4" />
            </span>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Communication drafts</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">Review prepared messages; nothing is sent automatically.</p>
            </div>
          </div>

          {!canReviewDrafts ? (
            <div className="mt-5 rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs leading-5 text-slate-600">Your role can view lifecycle workflows but does not have permission to review communication drafts.</p>
            </div>
          ) : drafts.error ? (
            <div className="mt-5">
              <LoadError message={drafts.error} onRetry={() => void loadDrafts()} />
            </div>
          ) : drafts.loading ? (
            <div className="mt-5 space-y-3" aria-label="Loading communication drafts">
              {[0, 1].map((item) => <div key={item} className="h-20 animate-pulse rounded-xl bg-white" />)}
            </div>
          ) : drafts.items.length === 0 ? (
            <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-white px-4 py-8 text-center">
              <CheckCircle2 className="mx-auto h-5 w-5 text-emerald-600" />
              <p className="mt-2 text-sm font-medium text-slate-700">No drafts awaiting review</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">New communication drafts will appear here when prepared.</p>
            </div>
          ) : (
            <ul className="mt-5 space-y-3">
              {drafts.items.map((draft) => (
                <li key={draft.id} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">{draft.student_name}</p>
                      <p className="mt-1 text-[10px] font-medium uppercase tracking-wide text-slate-500">{draft.category}</p>
                    </div>
                    <span className="shrink-0 rounded-full bg-sky-50 px-2 py-1 text-[10px] font-semibold capitalize text-sky-800">
                      {draft.status.replaceAll('_', ' ')}
                    </span>
                  </div>
                  <p className="mt-3 line-clamp-4 text-xs leading-5 text-slate-600">{draft.message}</p>
                  <p className="mt-3 flex items-center gap-1.5 border-t border-slate-100 pt-2.5 text-[10px] text-amber-800">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    {draft.requires_human_approval ? 'Approval required before sending' : 'Ready for staff review'}
                  </p>
                </li>
              ))}
            </ul>
          )}

          <a href="#student-roster" className="mt-5 inline-flex items-center gap-1 text-xs font-semibold text-indigo-700 hover:text-indigo-900">
            Go to learner roster <ArrowUpRight className="h-3.5 w-3.5" />
          </a>
        </aside>
      </div>
    </section>
  )
}

function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4">
      <div className="flex items-start gap-2.5">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-700" />
        <div className="min-w-0">
          <p className="text-xs font-semibold text-rose-900">This section did not respond</p>
          <p className="mt-1 text-xs leading-5 text-rose-800">{message}</p>
          <button type="button" onClick={onRetry} className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs font-semibold text-rose-800 hover:bg-rose-100">
            <RefreshCw className="h-3 w-3" /> Retry this section
          </button>
        </div>
      </div>
    </div>
  )
}
