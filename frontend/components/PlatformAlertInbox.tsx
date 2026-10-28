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
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-violet-600">Platform messages</p>
          <h2 className="mt-1 flex items-center gap-2 text-xl font-semibold text-slate-900">
            <Bell className="h-5 w-5" /> Sales &amp; Enrollment alerts
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Shared operational alerts. Read state and dismissal are private to your account.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void generateSummary()}
            disabled={working || inbox.alerts.length === 0}
            className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-violet-200 px-3 text-xs font-semibold text-violet-700 hover:bg-violet-50 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" /> Claude alert summary
          </button>
          <button
            type="button"
            onClick={() => void loadInbox()}
            disabled={loading}
            aria-label="Refresh alerts"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl bg-slate-50 p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Alerts</p>
          <p className="mt-1 text-xl font-bold text-slate-900">{inbox.total_count}</p>
        </div>
        <div className="rounded-xl bg-cyan-50 p-3">
          <p className="text-[10px] uppercase tracking-wide text-cyan-700">Unread for you</p>
          <p className="mt-1 text-xl font-bold text-cyan-900">{inbox.unread_count}</p>
        </div>
        <div className="rounded-xl bg-rose-50 p-3">
          <p className="text-[10px] uppercase tracking-wide text-rose-700">Critical</p>
          <p className="mt-1 text-xl font-bold text-rose-900">
            {inbox.critical_count}
          </p>
        </div>
      </div>

      {summary && (
        <div className="rounded-xl border border-violet-200 bg-violet-50 p-4" aria-live="polite">
          <p className="flex items-center gap-2 text-xs font-semibold text-violet-900">
            <Sparkles className="h-4 w-4" /> Claude summary
          </p>
          <p className="mt-2 text-sm leading-6 text-violet-950">{summary.summary}</p>
          <p className="mt-2 text-[11px] text-violet-700">
            Last 24 hours: {summary.counts.total_24h} alerts · {summary.counts.unread} unread · {summary.counts.critical_24h} critical
          </p>
        </div>
      )}

      {error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}

      {loading && inbox.alerts.length === 0 ? (
        <p className="py-6 text-center text-sm text-slate-500">Loading platform alerts…</p>
      ) : inbox.alerts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center">
          <Bell className="mx-auto h-6 w-6 text-slate-400" />
          <p className="mt-2 text-sm font-medium text-slate-700">No platform alerts</p>
          <p className="mt-1 text-xs text-slate-500">New Sales &amp; Enrollment operational alerts will appear here.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {inbox.alerts.map((alert) => {
            const chatStatus = (alert.details.google_chat as { status?: string } | undefined)?.status
            const contactId = typeof alert.details.contact_id === 'string' ? alert.details.contact_id : null
            const failureDetail = typeof alert.details.error === 'string' ? alert.details.error : null
            return (
              <article
                key={alert.id}
                className={`rounded-xl border p-4 ${alert.severity === 'critical' ? 'border-rose-200 bg-rose-50/60' : 'border-slate-200 bg-white'} ${alert.is_read ? 'opacity-75' : ''}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {alert.severity === 'critical' && <AlertTriangle className="h-4 w-4 text-rose-700" />}
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${alert.severity === 'critical' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-700'}`}>
                        {alert.severity}
                      </span>
                      <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{alert.type.replaceAll('_', ' ')}</span>
                      {!alert.is_read && <span className="rounded-full bg-cyan-100 px-2 py-0.5 text-[10px] font-bold uppercase text-cyan-800">Unread</span>}
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-900">{alert.message}</p>
                    {failureDetail && ['sales_scoring_failure', 'scoring_writeback_failure'].includes(alert.type) && (
                      <details className="mt-2 rounded-lg border border-rose-200 bg-white/80 px-3 py-2 text-xs text-rose-900">
                        <summary className="cursor-pointer font-semibold">Technical failure detail</summary>
                        <p className="mt-2 whitespace-pre-wrap break-words">{failureDetail}</p>
                      </details>
                    )}
                    <p className="mt-2 text-[11px] text-slate-500">
                      {alert.source} · {alert.created_at ? new Date(alert.created_at).toLocaleString() : 'Time unavailable'}
                      {chatStatus ? ` · Google Chat: ${chatStatus}` : ''}
                      {contactId ? ` · GHL contact ${contactId}` : ''}
                      {alert.result_id ? ` · Result ${alert.result_id}` : ''}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    {!alert.is_read && (
                      <button
                        type="button"
                        onClick={() => void updateAlert(alert.id, 'read')}
                        disabled={working}
                        className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
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
                        className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
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
