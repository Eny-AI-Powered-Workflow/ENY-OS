// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/KajabiConnectionSettings.tsx
'use client'

import { FormEvent, useCallback, useEffect, useState } from 'react'
import { API_TIMEOUTS, describeHttpError, fetchWithTimeout } from '@/lib/api'
import { usePermissions } from '@/lib/permissions'
import { supabase } from '@/lib/supabaseClient'

type KajabiConnection = {
  configured: boolean
  connected: boolean
  source: 'database' | 'environment' | 'not_configured'
  site_id: string | null
  last_validated_at: string | null
  can_disconnect: boolean
}

const API_URL = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/kajabi`

export default function KajabiConnectionSettings() {
  const { can } = usePermissions()
  const canManage = can('integrations:kajabi:manage')
  const [connection, setConnection] = useState<KajabiConnection | null>(null)
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [siteId, setSiteId] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const request = useCallback(async (path: string, init?: RequestInit) => {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) throw new Error('Your session has expired. Please sign in again.')
    const response = await fetchWithTimeout(
      `${API_URL}${path}`,
      {
        ...init,
        headers: {
          ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
          Authorization: `Bearer ${session.access_token}`,
          ...init?.headers,
        },
        credentials: 'include',
      },
      API_TIMEOUTS.standard,
    )
    if (!response.ok) throw new Error(await describeHttpError(response, 'Kajabi connection request failed.'))
    return response.json()
  }, [])

  const loadConnection = useCallback(async () => {
    if (!canManage) return
    setLoading(true)
    try {
      const status = await request('/connection') as KajabiConnection
      setConnection(status)
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load Kajabi connection status.')
    } finally {
      setLoading(false)
    }
  }, [canManage, request])

  useEffect(() => {
    void loadConnection()
  }, [loadConnection])

  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const status = await request('/connect', {
        method: 'POST',
        body: JSON.stringify({ client_id: clientId, client_secret: clientSecret, site_id: siteId }),
      }) as KajabiConnection
      setConnection(status)
      setClientId('')
      setClientSecret('')
      setSiteId('')
      setMessage('Kajabi credentials and Site ID were validated and saved securely.')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to connect Kajabi.')
    } finally {
      setClientSecret('')
      setSaving(false)
    }
  }

  async function disconnect() {
    if (!window.confirm('Remove the UI-managed Kajabi connection from the platform?')) return
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const status = await request('/connection', { method: 'DELETE' }) as KajabiConnection
      setConnection(status)
      setMessage(status.source === 'environment'
        ? 'The UI-managed credentials were removed. Kajabi is still configured in the backend environment; remove its KAJABI_CLIENT_ID, KAJABI_CLIENT_SECRET, and KAJABI_SITE_ID values there to fully disconnect.'
        : 'Kajabi has been disconnected from the platform.')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to disconnect Kajabi.')
    } finally {
      setSaving(false)
    }
  }

  if (!canManage) return null

  const connectionLabel = connection?.source === 'database'
    ? 'Connected with encrypted platform credentials'
    : connection?.source === 'environment'
      ? 'Configured in the backend environment'
      : 'Not connected'

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="kajabi-connection-heading">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 id="kajabi-connection-heading" className="text-lg font-semibold text-slate-900">Kajabi connection</h2>
          <p className="mt-1 text-sm text-slate-600">
            Connect the shared Kajabi Public API client for Student Success rosters, offers, and payments.
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${connection?.connected ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}`}>
          {loading ? 'Checking…' : connectionLabel}
        </span>
      </div>

      {connection?.connected && (
        <p className="mt-3 text-xs text-slate-600">
          Site ID: <span className="font-medium text-slate-800">{connection.site_id}</span>
          {connection.last_validated_at && ` · Last validated ${new Date(connection.last_validated_at).toLocaleString()}`}
        </p>
      )}
      {connection?.source === 'environment' && (
        <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          These credentials are managed in Render and cannot be removed from this screen. Saving below will securely replace them with a platform-managed connection.
        </p>
      )}

      <form className="mt-5 grid gap-4 md:grid-cols-3" onSubmit={(event) => void connect(event)}>
        <label className="text-sm font-medium text-slate-700">
          Kajabi Client ID
          <input
            required
            autoComplete="off"
            value={clientId}
            onChange={(event) => setClientId(event.target.value)}
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Kajabi Client Secret
          <input
            required
            type="password"
            autoComplete="new-password"
            value={clientSecret}
            onChange={(event) => setClientSecret(event.target.value)}
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Kajabi Site ID
          <input
            required
            autoComplete="off"
            value={siteId}
            onChange={(event) => setSiteId(event.target.value)}
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3 md:col-span-3">
          <button
            type="submit"
            disabled={saving || loading}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? 'Validating…' : connection?.connected ? 'Validate and update connection' : 'Connect Kajabi'}
          </button>
          {connection?.can_disconnect && (
            <button
              type="button"
              onClick={() => void disconnect()}
              disabled={saving}
              className="rounded-lg border border-rose-300 px-4 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
            >
              Disconnect
            </button>
          )}
          <p className="text-xs text-slate-500">
            Credentials are sent to the backend, validated before saving, and encrypted at rest. They are never returned to the browser.
          </p>
        </div>
      </form>

      {error && <p role="alert" className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {message && <p role="status" className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}
    </section>
  )
}
