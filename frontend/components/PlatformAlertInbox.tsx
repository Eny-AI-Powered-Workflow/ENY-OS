// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/PlatformAlertInbox.tsx
'use client'

import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, Bell, Check, RefreshCw, Sparkles, Trash2 } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type PlatformAlert = {
  id: string
  type: string
  severity: string
  source: string
  message: string
  result_id: string | null
  status: string
  details: Record<string, unknown>
  created_at: string | null
  read_at: string | null
  is_read: boolean
}

type InboxResponse = {
  alerts: PlatformAlert[]
  total_count: number
  unread_count: number
  critical_count: number
}

type AlertSummary = {
  summary: string
  counts: { total_24h: number; unread: number; critical_24h: number }
  generated_at: string
}

export default function PlatformAlertInbox() {
  const { can } = usePermissions()
  const canDismiss = can('sales:alerts:manage')
  const [inbox, setInbox] = useState<InboxResponse>({ alerts: [], total_count: 0, unread_count: 0, critical_count: 0 })
  const [summary, setSummary] = useState<AlertSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const authenticatedFetch = useCallback(async (path: string, options: RequestInit = {}) => {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) throw new Error('Your session expired. Sign in again to view platform alerts.')
    return fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment${path}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        ...(options.headers || {}),
      },
      credentials: 'include',
    })
  }, [])

  const loadInbox = useCallback(async () => {
    setLoading(true)
    try {
      const response = await authenticatedFetch('/alerts/inbox?limit=100')
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load platform alerts.')
      }
      setInbox(payload)
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load platform alerts.')
    } finally {
      setLoading(false)
    }
  }, [authenticatedFetch])

  useEffect(() => {
    void loadInbox()
    const timer = window.setInterval(() => void loadInbox(), 30_000)
    return () => window.clearInterval(timer)
  }, [loadInbox])

  const updateAlert = async (alertId: string, action: 'read' | 'inbox') => {
    setWorking(true)
    setError(null)
    try {
      const response = await authenticatedFetch(`/alerts/${alertId}/${action}`, {
        method: action === 'read' ? 'POST' : 'DELETE',
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to update this alert.')
      }
      await loadInbox()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to update this alert.')
    } finally {
      setWorking(false)
    }
  }

  const generateSummary = async () => {
    setWorking(true)
    setError(null)
    try {
      const response = await authenticatedFetch('/alerts/ai-summary', { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Claude could not summarize the alerts.')
      }
      setSummary(payload)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Claude could not summarize the alerts.')
    } finally {
      setWorking(false)
    }
  }

  return (
    <section className="space-y-5 rounded-2xl border border-slate-800/90 bg-[#0e1222] p-4 shadow-2xl sm:space-y-6 sm:p-6">
      <div className="flex flex-col justify-between gap-4 border-b border-slate-800/80 pb-5 sm:flex-row sm:items-center">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-indigo-400">Platform messages</p>
          <h2 className="mt-1 flex items-center gap-2 text-lg font-semibold tracking-tight text-white">
            <Bell className="h-4 w-4 text-indigo-400" /> Sales &amp; Enrollment alerts
          </h2>
          <p className="mt-1 text-xs text-slate-400">
            Shared operational alerts. Read state and dismissal are private to your account.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void generateSummary()}
            disabled={working || inbox.alerts.length === 0}
            className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-violet-800/70 bg-violet-950/40 px-3 text-xs font-semibold text-violet-200 transition hover:border-violet-600/70 hover:bg-violet-900/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" /> Claude alert summary
          </button>
          <button
            type="button"
            onClick={() => void loadInbox()}
            disabled={loading}
            aria-label="Refresh alerts"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-900/70 text-slate-300 transition hover:border-slate-600 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-[#121729] p-4 transition hover:border-slate-700">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Alerts</p>
          <p className="mt-1 text-2xl font-extrabold tracking-tight text-white">{inbox.total_count}</p>
          <p className="mt-1 text-[10px] text-slate-500">Total active in inbox</p>
        </div>
        <div className="relative overflow-hidden rounded-xl border border-cyan-900/50 bg-[#0b1c2b]/70 p-4 transition hover:border-cyan-700/60">
          <p className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">Unread for you</p>
          <p className="mt-1 text-2xl font-extrabold tracking-tight text-cyan-300">{inbox.unread_count}</p>
          <p className="mt-1 flex items-center gap-1.5 text-[10px] text-cyan-400/80">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            Action required by you
          </p>
        </div>
        <div className="relative overflow-hidden rounded-xl border border-rose-900/50 bg-[#24111d]/60 p-4 transition hover:border-rose-700/60">
          <p className="text-[10px] font-bold uppercase tracking-wider text-rose-400">Critical</p>
          <p className="mt-1 text-2xl font-extrabold tracking-tight text-rose-300">
            {inbox.critical_count}
          </p>
          <p className="mt-1 flex items-center gap-1.5 text-[10px] text-rose-400/80">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
            Unresolved critical alerts
          </p>
        </div>
      </div>

      {summary && (
        <div className="rounded-xl border border-violet-800/50 bg-violet-950/30 p-4" aria-live="polite">
          <p className="flex items-center gap-2 text-xs font-semibold text-violet-200">
            <Sparkles className="h-4 w-4" /> Claude summary
          </p>
          <p className="mt-2 text-sm leading-6 text-violet-100">{summary.summary}</p>
          <p className="mt-2 text-[11px] text-violet-300">
            Last 24 hours: {summary.counts.total_24h} alerts · {summary.counts.unread} unread · {summary.counts.critical_24h} critical
          </p>
        </div>
      )}

      {error && <p role="alert" className="rounded-lg border border-rose-900/60 bg-rose-950/40 p-3 text-sm text-rose-200">{error}</p>}

      {loading && inbox.alerts.length === 0 ? (
        <p role="status" className="py-6 text-center text-sm text-slate-400">Loading platform alerts…</p>
      ) : inbox.alerts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-700 p-8 text-center">
          <Bell className="mx-auto h-6 w-6 text-slate-500" />
          <p className="mt-2 text-sm font-medium text-slate-200">No platform alerts</p>
          <p className="mt-1 text-xs text-slate-400">New Sales &amp; Enrollment operational alerts will appear here.</p>
        </div>
      ) : (
        <div className="space-y-3 pt-1" aria-label="Platform alert feed">
          {inbox.alerts.map((alert) => {
            const chatStatus = (alert.details.google_chat as { status?: string } | undefined)?.status
            const contactId = typeof alert.details.contact_id === 'string' ? alert.details.contact_id : null
            const failureDetail = typeof alert.details.error === 'string' ? alert.details.error : null
            return (
              <article
                key={alert.id}
                className={`rounded-xl border p-4 transition sm:p-5 ${
                  alert.severity === 'critical'
                    ? 'border-rose-900/50 bg-[linear-gradient(180deg,rgba(244,63,94,0.045)_0%,rgba(17,21,40,0.65)_100%)] hover:border-rose-800/70'
                    : 'border-slate-800 bg-[#111528]/80 hover:border-slate-700'
                } ${alert.is_read ? 'opacity-75' : ''}`}
              >
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div className="flex min-w-0 flex-1 items-start gap-3">
                    <div className={`mt-0.5 shrink-0 rounded-md border p-1.5 ${
                      alert.severity === 'critical'
                        ? 'border-rose-500/20 bg-rose-500/10 text-rose-400'
                        : 'border-slate-700 bg-slate-800/70 text-slate-400'
                    }`}>
                      <AlertTriangle className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                        alert.severity === 'critical'
                          ? 'border-rose-500/25 bg-rose-500/10 text-rose-300'
                          : 'border-slate-700 bg-slate-800 text-slate-300'
                      }`}>
                        {alert.severity}
                      </span>
                      <span className="rounded-md border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-300">
                        {alert.type.replaceAll('_', ' ')}
                      </span>
                      {!alert.is_read && <span className="rounded-md border border-cyan-500/25 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-cyan-300">Unread</span>}
                    </div>
                    <p className="mt-2 text-sm font-semibold leading-6 text-white">{alert.message}</p>
                    {failureDetail && ['sales_scoring_failure', 'scoring_writeback_failure'].includes(alert.type) && (
                      <details className="group/details mt-3 rounded-lg border border-rose-900/40 bg-rose-950/20 p-3 text-xs text-rose-300">
                        <summary className="cursor-pointer select-none font-semibold hover:text-rose-200">Technical failure detail</summary>
                        <p className="mt-2 whitespace-pre-wrap break-words rounded border border-rose-900/30 bg-rose-950/40 px-3 py-2 font-mono">{failureDetail}</p>
                      </details>
                    )}
                    <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-slate-800/80 pt-3 text-[11px] text-slate-400">
                      <span className="inline-flex items-center gap-1.5 font-semibold text-purple-300">
                        <span className="h-1.5 w-1.5 rounded-full bg-purple-400" />
                        {alert.source}
                      </span>
                      <span className="text-slate-600">·</span>
                      <span>{alert.created_at ? new Date(alert.created_at).toLocaleString() : 'Time unavailable'}</span>
                      {chatStatus && <><span className="text-slate-600">·</span><span>Google Chat: <span className="text-slate-300">{chatStatus}</span></span></>}
                      {contactId && <><span className="text-slate-600">·</span><span>GHL contact <span className="font-mono text-slate-300">{contactId}</span></span></>}
                      {alert.result_id && <><span className="text-slate-600">·</span><span>Result <span className="font-mono text-slate-300">{alert.result_id}</span></span></>}
                    </div>
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-2 sm:self-start">
                    {!alert.is_read && (
                      <button
                        type="button"
                        onClick={() => void updateAlert(alert.id, 'read')}
                        disabled={working}
                        className="inline-flex min-h-8 items-center gap-1.5 rounded-lg border border-slate-600/80 bg-slate-800 px-2.5 text-xs font-medium text-slate-200 transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <Check className="h-3.5 w-3.5" /> Mark read
                      </button>
                    )}
                    {canDismiss && (
                      <button
                        type="button"
                        onClick={() => void updateAlert(alert.id, 'inbox')}
                        disabled={working}
                        aria-label="Dismiss this alert from your inbox"
                        title="Dismiss for me; the shared record is retained"
                        className="inline-flex min-h-8 items-center gap-1.5 rounded-lg border border-slate-700/80 bg-slate-900/90 px-2.5 text-xs font-medium text-slate-300 transition hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Dismiss
                      </button>
                    )}
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
