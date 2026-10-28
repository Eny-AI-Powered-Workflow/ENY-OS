// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/SocialAnalytics.tsx
'use client'

import { useEffect, useState } from 'react'
import { Activity, RefreshCw } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type Metric = {
  value: number
  unit: string
  latest_observed_at?: string
  reporting_platforms?: string[]
  missing_platforms?: string[]
}

type PlatformStats = {
  credentials_status: string
  missing_credentials: string[]
  publishing_status: string
  missing_publishing_configuration: string[]
  api_collector_status: string
  metrics_collection_status: string
  ghl_connection_status: string
  insights_supported: boolean
  connected_account_count: number
  accounts: Array<{
    id: string
    name: string
    type: string | null
    active: boolean
    expired: boolean
    synced_at: string
  }>
  recent_posts: Array<{
    id: string
    text: string | null
    permalink: string | null
    published_at: string
    metrics: Record<string, number>
  }>
  stats_status: string
  posts_count: number
  metrics: Record<string, Metric>
  latest_observed_at: string | null
}

type Analytics = {
  period_days: number
  platforms: Record<string, PlatformStats>
  collective: {
    platform_count: number
    reporting_platforms: string[]
    missing_platforms: string[]
    posts_count: number
    metrics: Record<string, Metric>
  }
  notes: string[]
}

const platformOrder = ['facebook', 'linkedin', 'instagram', 'tiktok', 'pinterest', 'youtube', 'x']
const metricOrder = ['impressions', 'reach', 'likes', 'comments', 'shares', 'saves', 'clicks', 'views', 'watch_time_seconds']
const platformLabels: Record<string, string> = {
  linkedin: 'LinkedIn',
  instagram: 'Instagram',
  facebook: 'Facebook',
  x: 'X',
  tiktok: 'TikTok',
  pinterest: 'Pinterest',
  youtube: 'YouTube',
}
const metricLabels: Record<string, string> = {
  impressions: 'Impressions',
  reach: 'Reach',
  likes: 'Likes / reactions',
  comments: 'Comments',
  shares: 'Shares',
  saves: 'Saves',
  clicks: 'Clicks',
  views: 'Views',
  watch_time_seconds: 'Watch time (seconds)',
}

function formatMetric(metric: Metric | undefined): string {
  if (!metric) return 'No data'
  return metric.value.toLocaleString(undefined, { maximumFractionDigits: 1 })
}

export default function SocialAnalytics() {
  const { can } = usePermissions()
  const canSocial = can('marketing:social')
  const [days, setDays] = useState(30)
  const [report, setReport] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncSummary, setSyncSummary] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const canSync = can('marketing:integrations')

  const load = async () => {
    if (!canSocial) return
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const headers: HeadersInit = session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/social/analytics?days=${days}`,
        { headers, credentials: 'include' },
      )
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load social analytics')
      }
      setReport(payload)
      setError(null)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to load social analytics')
    } finally {
      setLoading(false)
    }
  }

  const syncFromGhl = async () => {
    if (!canSync) return
    setSyncing(true)
    setSyncSummary(null)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const headers: HeadersInit = session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/social/analytics/sync?days=${days}`,
        { method: 'POST', headers, credentials: 'include' },
      )
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to sync GHL social data')
      }
      const summaryParts = [
        `GHL sync complete: ${payload.accounts_synced} accounts, ${payload.posts_processed} posts, and ${payload.metrics_recorded} engagement values stored.`,
      ]
      if (payload.skipped_posts) summaryParts.push(`${payload.skipped_posts} posts could not be normalized.`)
      if (payload.max_posts_reached) summaryParts.push('The 5,000-post sync limit was reached; narrow the date range to retrieve all posts.')
      setSyncSummary(summaryParts.join(' '))
      setError(null)
      await load()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to sync GHL social data')
    } finally {
      setSyncing(false)
    }
  }

  useEffect(() => { void load() }, [canSocial, days])

  if (!canSocial) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="font-semibold text-slate-900">Social platform analytics</h2>
        <p className="mt-1 text-sm text-slate-500">Your role does not have access to social analytics.</p>
      </section>
    )
  }

  const platformName = (platform: string) => platformLabels[platform] || platform

  return (
    <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-rose-700" />
            <h2 className="text-xl font-semibold text-slate-950">Social platform analytics</h2>
          </div>
          <p className="mt-1 max-w-3xl text-xs text-slate-500">
            GHL-synced post details and independent platform stats. Collective totals include only platforms returning each metric.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="social-analytics-days" className="text-xs text-slate-500">Published in</label>
          <select
            id="social-analytics-days"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
            className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs"
          >
            {[7, 30, 90, 365].map((value) => <option key={value} value={value}>{value} days</option>)}
          </select>
          <button type="button" onClick={() => void load()} aria-label="Refresh social analytics" className="rounded-md border border-slate-200 p-2 text-slate-600 hover:bg-slate-50">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {canSync && (
            <button
              type="button"
              onClick={() => void syncFromGhl()}
              disabled={syncing}
              className="inline-flex items-center gap-2 rounded-md bg-indigo-700 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-800 disabled:cursor-wait disabled:opacity-60"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Syncing GHL…' : 'Sync from GHL'}
            </button>
          )}
        </div>
      </div>

      {error && <p role="alert" className="rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">{error}</p>}
      {syncSummary && <p role="status" className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">{syncSummary}</p>}
      {!canSync && <p className="text-xs text-slate-500">Your role can view stored analytics but does not have permission to sync from GHL.</p>}
      {report && (
        <>
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold text-indigo-950">Collective overview</h3>
                <p className="mt-1 text-xs text-indigo-800">
                  {report.collective.reporting_platforms.length} of {report.collective.platform_count} platforms reporting
                  {' · '}{report.collective.posts_count.toLocaleString()} posts
                </p>
              </div>
              {!!report.collective.missing_platforms.length && (
                <p className="text-right text-xs text-indigo-800">
                  Waiting on: {report.collective.missing_platforms.map(platformName).join(', ')}
                </p>
              )}
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              {metricOrder.map((key) => {
                const metric = report.collective.metrics[key]
                return (
                  <div key={key} className="rounded-lg border border-indigo-100 bg-white p-3">
                    <p className="text-[11px] text-slate-500">{metricLabels[key]}</p>
                    <p className="mt-1 text-lg font-semibold text-slate-900">{formatMetric(metric)}</p>
                    <p className="mt-1 text-[10px] text-slate-500">
                      {metric
                        ? `Reported by ${metric.reporting_platforms?.map(platformName).join(', ')}`
                        : 'No platform has reported this metric'}
                    </p>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {platformOrder.map((platform) => {
              const stats = report.platforms[platform]
              return (
                <article key={platform} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-semibold capitalize text-slate-900">{platformName(platform)}</h3>
                      <p className="mt-1 text-[11px] text-slate-500">
                        {stats.posts_count.toLocaleString()} published posts · {stats.connected_account_count} connected accounts
                      </p>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${
                      stats.stats_status === 'available'
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-amber-50 text-amber-800'
                    }`}>
                      {stats.stats_status === 'available'
                        ? 'Insights available'
                        : stats.stats_status === 'awaiting_metrics'
                          ? 'Awaiting insights'
                          : stats.stats_status === 'posts_only'
                            ? 'Posts only in GHL'
                            : 'No data yet'}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5 text-[10px]">
                    <span className={`rounded px-2 py-1 ${stats.ghl_connection_status === 'configured' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                      GHL {stats.ghl_connection_status}
                    </span>
                    <span className={`rounded px-2 py-1 ${stats.insights_supported ? 'bg-indigo-50 text-indigo-700' : 'bg-slate-100 text-slate-600'}`}>
                      {stats.insights_supported ? 'Post insights supported' : 'GHL post insights unavailable'}
                    </span>
                  </div>
                  <p className="mt-2 text-[10px] leading-relaxed text-amber-800">
                    {stats.insights_supported
                      ? 'GHL provides likes, comments, and shares for this platform. Sync to refresh its posts and metrics.'
                      : 'GHL can sync this platform’s published posts, but does not provide post engagement metrics for it.'}
                  </p>
                  {stats.accounts.length > 0 && (
                    <ul className="mt-2 space-y-1 text-[10px] text-slate-600">
                      {stats.accounts.map((account) => (
                        <li key={account.id} className="flex items-center justify-between gap-2">
                          <span className="truncate">{account.name}</span>
                          <span className={account.active && !account.expired ? 'text-emerald-700' : 'text-amber-700'}>
                            {account.expired ? 'Expired' : account.active ? 'Connected' : 'Inactive'}
                          </span>
                          <span className="shrink-0 text-slate-400">
                            Synced {new Date(account.synced_at).toLocaleDateString()}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {stats.ghl_connection_status !== 'configured' && (
                    <p className="mt-1 break-words text-[10px] text-slate-500">
                      Configure GHL_PRIVATE_TOKEN and GHL_LOCATION_ID on the backend to enable sync.
                    </p>
                  )}
                  <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 border-t border-slate-100 pt-3">
                    {metricOrder.map((key) => (
                      <div key={key} className="flex items-baseline justify-between gap-2 text-xs">
                        <span className="text-slate-500">{metricLabels[key]}</span>
                        <strong className="text-slate-800">{formatMetric(stats.metrics[key])}</strong>
                      </div>
                    ))}
                  </div>
                  {stats.recent_posts.length > 0 && (
                    <div className="mt-3 border-t border-slate-100 pt-3">
                      <h4 className="text-[11px] font-semibold text-slate-700">Recent posts</h4>
                      <ul className="mt-2 space-y-2">
                        {stats.recent_posts.map((post) => (
                          <li key={post.id} className="rounded-lg bg-slate-50 p-2.5">
                            <p className="line-clamp-2 text-[11px] leading-relaxed text-slate-700">
                              {post.text || 'Published post'}
                            </p>
                            <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-[10px] text-slate-500">
                              <time dateTime={post.published_at}>{new Date(post.published_at).toLocaleDateString()}</time>
                              <span>
                                {['likes', 'comments', 'shares']
                                  .filter((key) => post.metrics[key] !== undefined)
                                  .map((key) => `${metricLabels[key]} ${post.metrics[key].toLocaleString()}`)
                                  .join(' · ') || 'No GHL insights'}
                              </span>
                              {post.permalink && (
                                <a href={post.permalink} target="_blank" rel="noopener noreferrer" className="font-medium text-indigo-700 hover:underline">
                                  View post
                                </a>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {stats.latest_observed_at && (
                    <p className="mt-3 text-[10px] text-slate-400">
                      Latest observation {new Date(stats.latest_observed_at).toLocaleString()}
                    </p>
                  )}
                </article>
              )
            })}
          </div>

          <div className="space-y-1 border-t border-slate-100 pt-3">
            {report.notes.map((note) => <p key={note} className="text-[10px] leading-relaxed text-slate-500">{note}</p>)}
          </div>
        </>
      )}
      {!report && !loading && !error && <p className="text-sm text-slate-500">No social analytics report is available.</p>}
    </section>
  )
}
