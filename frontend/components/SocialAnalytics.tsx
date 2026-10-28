// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/SocialAnalytics.tsx
'use client'

import { useEffect, useState, type ReactNode } from 'react'
import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  Facebook,
  Instagram,
  Linkedin,
  MessageCircle,
  RefreshCw,
  Share2,
  ThumbsUp,
  Youtube,
} from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type Metric = {
  value: number
  unit: string
  latest_observed_at?: string
  reporting_platforms?: string[]
  missing_platforms?: string[]
}

type SocialAccount = {
  id: string
  name: string
  type: string | null
  active: boolean
  expired: boolean
  synced_at: string
}

type SocialPost = {
  id: string
  text: string | null
  permalink: string | null
  published_at: string
  metrics: Record<string, number>
}

type PlatformStats = {
  ghl_connection_status: string
  insights_supported: boolean
  connected_account_count: number
  accounts: SocialAccount[]
  recent_posts: SocialPost[]
  stats_status: string
  posts_count: number
  metrics: Record<string, Metric>
  latest_observed_at: string | null
}

type Analytics = {
  period_days: number
  period_start: string
  period_end: string
  sync: {
    status: 'connected' | 'error' | 'not_synced'
    last_attempted_at: string | null
    last_success_at: string | null
    last_error: string | null
    last_period_days: number | null
    accounts_synced: number
    posts_processed: number
    metrics_recorded: number
  }
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

const platformOrder = ['facebook', 'instagram', 'linkedin', 'tiktok', 'pinterest', 'youtube', 'x']
const metricOrder = ['likes', 'comments', 'shares']
const platformLabels: Record<string, string> = {
  facebook: 'Facebook',
  instagram: 'Instagram',
  linkedin: 'LinkedIn',
  tiktok: 'TikTok',
  pinterest: 'Pinterest',
  youtube: 'YouTube',
  x: 'X',
}
const platformStyles: Record<string, { icon: typeof Facebook; color: string; chip: string }> = {
  facebook: { icon: Facebook, color: 'bg-blue-600', chip: 'text-blue-700 bg-blue-50' },
  instagram: { icon: Instagram, color: 'bg-fuchsia-600', chip: 'text-fuchsia-700 bg-fuchsia-50' },
  linkedin: { icon: Linkedin, color: 'bg-sky-700', chip: 'text-sky-800 bg-sky-50' },
  tiktok: { icon: Activity, color: 'bg-slate-950', chip: 'text-slate-700 bg-slate-100' },
  pinterest: { icon: Activity, color: 'bg-rose-700', chip: 'text-rose-700 bg-rose-50' },
  youtube: { icon: Youtube, color: 'bg-red-600', chip: 'text-red-700 bg-red-50' },
  x: { icon: Activity, color: 'bg-slate-900', chip: 'text-slate-700 bg-slate-100' },
}
const metricLabels: Record<string, string> = {
  likes: 'Likes',
  comments: 'Comments',
  shares: 'Shares',
}
const AUTO_SYNC_INTERVAL_MS = 15 * 60 * 1000

function formatNumber(value: number | undefined): string {
  return typeof value === 'number'
    ? new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(value)
    : '—'
}

function formatDate(value: string | null | undefined): string {
  if (!value) return 'Not synced yet'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? 'Unknown'
    : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function totalInteractions(metrics: Record<string, Metric>): number {
  return metricOrder.reduce((total, key) => total + (metrics[key]?.value ?? 0), 0)
}

function getErrorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = payload.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}

export default function SocialAnalytics() {
  const { can } = usePermissions()
  const canSocial = can('marketing:social')
  const canSync = can('marketing:social:sync')
  const [days, setDays] = useState(30)
  const [report, setReport] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const authHeaders = async (): Promise<HeadersInit> => {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token
      ? { Authorization: `Bearer ${session.access_token}` }
      : {}
  }

  const load = async (showLoading = true): Promise<Analytics | null> => {
    if (!canSocial) return null
    if (showLoading) setLoading(true)
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/social/analytics?days=${days}`,
        { headers: await authHeaders(), credentials: 'include', cache: 'no-store' },
      )
      const payload = await response.json()
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Unable to load social analytics'))
      setReport(payload as Analytics)
      setError(null)
      return payload as Analytics
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to load social analytics')
      return null
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  const syncFromGhl = async (quiet = false): Promise<boolean> => {
    if (!canSync) return false
    setSyncing(true)
    if (!quiet) setError(null)
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/marketing/social/analytics/sync?days=${days}`,
        {
          method: 'POST',
          headers: await authHeaders(),
          credentials: 'include',
          cache: 'no-store',
        },
      )
      const payload = await response.json()
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Unable to sync GHL social data'))
      await load(false)
      return true
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Unable to sync GHL social data'
      await load(false)
      setError(message)
      return false
    } finally {
      setSyncing(false)
    }
  }

  useEffect(() => {
    let active = true
    const initialize = async () => {
      const currentReport = await load()
      if (!active || !canSync || !currentReport) return
      const lastSuccess = currentReport.sync.last_success_at
        ? new Date(currentReport.sync.last_success_at).getTime()
        : 0
      const stale = !lastSuccess
        || Date.now() - lastSuccess >= AUTO_SYNC_INTERVAL_MS
        || currentReport.sync.last_period_days !== days
      if (stale) await syncFromGhl(true)
    }
    void initialize()
    return () => { active = false }
  }, [canSocial, canSync, days])

  if (!canSocial) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="font-semibold text-slate-900">Social platform analytics</h2>
        <p className="mt-1 text-sm text-slate-500">Your role does not have access to social analytics.</p>
      </section>
    )
  }

  const platforms: Record<string, PlatformStats> = report?.platforms ?? {}
  const connectedAccounts = platformOrder.reduce(
    (total, platform) => total + (platforms[platform]?.connected_account_count ?? 0),
    0,
  )
  const insightPlatforms = platformOrder.filter(
    (platform) => Boolean(
      platforms[platform]?.insights_supported
      && (platforms[platform]?.connected_account_count ?? 0) > 0,
    ),
  )
  const reportingPlatforms = report?.collective.reporting_platforms ?? []
  const reportedInsightPlatforms = reportingPlatforms.filter((platform) => insightPlatforms.includes(platform))
  const interactions = report ? totalInteractions(report.collective.metrics) : 0
  const maxPlatformInteractions = Math.max(
    1,
    ...platformOrder.map((platform) => totalInteractions(platforms[platform]?.metrics ?? {})),
  )
  const syncFresh = report?.sync.last_success_at
    ? Date.now() - new Date(report.sync.last_success_at).getTime() < AUTO_SYNC_INTERVAL_MS
    : false

  return (
    <section className="overflow-hidden rounded-3xl border border-slate-200 bg-slate-50 shadow-sm">
      <header className="bg-gradient-to-br from-slate-950 via-indigo-950 to-indigo-800 px-5 py-6 text-white sm:px-7">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <div className="flex items-center gap-2 text-indigo-200">
              <Activity className="h-4 w-4" />
              <span className="text-xs font-semibold uppercase tracking-[0.18em]">Marketing intelligence</span>
            </div>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Social performance</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-indigo-100/80">
              Published content and engagement reported by GoHighLevel Social Planner.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="social-analytics-days" className="sr-only">Published within</label>
            <select
              id="social-analytics-days"
              value={days}
              onChange={(event) => setDays(Number(event.target.value))}
              className="rounded-xl border border-white/20 bg-white/10 px-3 py-2.5 text-sm font-medium text-white outline-none hover:bg-white/15 focus:ring-2 focus:ring-white/60 [&>option]:text-slate-900"
            >
              {[7, 30, 90, 365].map((value) => <option key={value} value={value}>{value} days</option>)}
            </select>
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading || syncing}
              aria-label="Refresh social analytics"
              className="rounded-xl border border-white/20 bg-white/10 p-2.5 text-white hover:bg-white/15 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            {canSync && (
              <button
                type="button"
                onClick={() => void syncFromGhl()}
                disabled={syncing || loading}
                className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-indigo-950 shadow-sm hover:bg-indigo-50 disabled:cursor-wait disabled:opacity-60"
              >
                <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? 'Syncing…' : 'Sync now'}
              </button>
            )}
          </div>
        </div>
        <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-white/15 pt-4 text-xs text-indigo-100/80">
          <span className="inline-flex items-center gap-1.5">
            {syncing
              ? <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              : report?.sync.status === 'connected'
                ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" />
                : <Clock3 className="h-3.5 w-3.5" />}
            {syncing ? 'Refreshing from GHL' : syncFresh ? 'Live data · refreshed recently' : 'Snapshot data'}
          </span>
          <span>Last successful sync: {formatDate(report?.sync.last_success_at)}</span>
          {report?.sync.last_period_days && (
            <span>Sync window: {report.sync.last_period_days} days</span>
          )}
        </div>
      </header>

      <div className="space-y-6 p-4 sm:p-6">
        {error && (
          <div role="alert" className="flex flex-col gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-rose-900">We couldn’t refresh social data</p>
              <p className="mt-1 text-sm text-rose-800">{error}</p>
              {report?.sync.last_success_at && (
                <p className="mt-1 text-xs text-rose-700">Showing the last successful snapshot from {formatDate(report.sync.last_success_at)}.</p>
              )}
            </div>
            {canSync && (
              <button type="button" onClick={() => void syncFromGhl()} className="shrink-0 rounded-lg border border-rose-300 bg-white px-3 py-2 text-xs font-semibold text-rose-800 hover:bg-rose-100">
                Retry sync
              </button>
            )}
          </div>
        )}

        {loading && !report ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Loading social analytics">
            {[0, 1, 2, 3].map((item) => (
              <div key={item} className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-white" />
            ))}
          </div>
        ) : report ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard label="Published posts" value={formatNumber(report.collective.posts_count)} detail={`In the last ${days} days`} icon={Activity} tone="indigo" />
              <KpiCard label="Connected accounts" value={formatNumber(connectedAccounts)} detail={`${report.collective.platform_count} networks tracked`} icon={CheckCircle2} tone="emerald" />
              <KpiCard label="Tracked interactions" value={formatNumber(interactions)} detail={`${reportingPlatforms.length} networks reporting`} icon={ThumbsUp} tone="amber" />
              <KpiCard label="Insight coverage" value={`${reportedInsightPlatforms.length} / ${insightPlatforms.length}`} detail="Networks reporting GHL post insights" icon={Share2} tone="violet" />
            </div>

            <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
              <section className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">Engagement by network</h3>
                    <p className="mt-1 text-xs text-slate-500">Likes, comments and shares available from GHL for this period.</p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                    {reportingPlatforms.length} reporting
                  </span>
                </div>
                <div className="mt-5 space-y-4">
                  {platformOrder.filter((platform) => platforms[platform]?.insights_supported).map((platform) => {
                    const stats = platforms[platform]
                    const amount = totalInteractions(stats.metrics)
                    const style = platformStyles[platform]
                    const Icon = style.icon
                    return (
                      <div key={platform} className="grid grid-cols-[112px_1fr_54px] items-center gap-3">
                        <div className="flex items-center gap-2 text-xs font-medium text-slate-700">
                          <span className={`flex h-7 w-7 items-center justify-center rounded-lg text-white ${style.color}`}>
                            <Icon className="h-3.5 w-3.5" />
                          </span>
                          {platformLabels[platform]}
                        </div>
                        <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className={`h-full rounded-full transition-all ${style.color}`}
                            style={{ width: `${amount ? Math.max(3, (amount / maxPlatformInteractions) * 100) : 0}%` }}
                          />
                        </div>
                        <span className="text-right text-xs font-semibold tabular-nums text-slate-800">{formatNumber(amount)}</span>
                      </div>
                    )
                  })}
                </div>
                {reportingPlatforms.length === 0 && (
                  <EmptyState
                    title="No engagement insights yet"
                    description="Sync GHL to load published posts. Insights appear when Social Planner has received post-level likes, comments or shares."
                  />
                )}
                <p className="mt-5 border-t border-slate-100 pt-3 text-[11px] leading-5 text-slate-500">
                  This is a period total of the latest available values per post, not a daily trend. GHL returns only selected engagement counts; platform totals are not full-reach comparisons.
                </p>
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">Network coverage</h3>
                    <p className="mt-1 text-xs text-slate-500">Account and insight availability at a glance.</p>
                  </div>
                  <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-medium text-indigo-700">
                    {connectedAccounts} active
                  </span>
                </div>
                <ul className="mt-4 divide-y divide-slate-100">
                  {platformOrder.map((platform) => {
                    const stats = platforms[platform]
                    const style = platformStyles[platform]
                    const Icon = style.icon
                    return (
                      <li key={platform} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                        <div className="flex min-w-0 items-center gap-2.5">
                          <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-white ${style.color}`}>
                            <Icon className="h-4 w-4" />
                          </span>
                          <div className="min-w-0">
                            <p className="truncate text-xs font-semibold text-slate-800">{platformLabels[platform]}</p>
                            <p className="text-[11px] text-slate-500">
                              {stats.connected_account_count} account{stats.connected_account_count === 1 ? '' : 's'} · {stats.posts_count} posts
                            </p>
                          </div>
                        </div>
                        <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold ${stats.stats_status === 'available' ? 'bg-emerald-50 text-emerald-700' : stats.stats_status === 'posts_only' ? 'bg-blue-50 text-blue-700' : 'bg-slate-100 text-slate-600'}`}>
                          {stats.stats_status === 'available'
                            ? 'Insights'
                            : stats.stats_status === 'posts_only'
                              ? 'Posts only'
                              : stats.insights_supported
                                ? 'Awaiting insights'
                                : 'No posts'}
                        </span>
                      </li>
                    )
                  })}
                </ul>
              </section>
            </div>

            <section>
              <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">Platform detail</h3>
                  <p className="mt-1 text-xs text-slate-500">Recent published posts and the metrics GHL currently exposes.</p>
                </div>
                <p className="text-[11px] text-slate-500">
                  {report.period_start.slice(0, 10)} — {report.period_end.slice(0, 10)}
                </p>
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {platformOrder.map((platform) => {
                  const stats = platforms[platform]
                  const style = platformStyles[platform]
                  const Icon = style.icon
                  return (
                    <article key={platform} className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <span className={`flex h-9 w-9 items-center justify-center rounded-xl text-white ${style.color}`}>
                            <Icon className="h-4 w-4" />
                          </span>
                          <div>
                            <h4 className="text-sm font-semibold text-slate-900">{platformLabels[platform]}</h4>
                            <p className="text-[11px] text-slate-500">{stats.connected_account_count} connected · {stats.posts_count} posts</p>
                          </div>
                        </div>
                        {stats.ghl_connection_status === 'configured' && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold text-emerald-700">
                            <CheckCircle2 className="h-3 w-3" /> GHL
                          </span>
                        )}
                      </div>
                      {stats.accounts.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 px-4 pt-3">
                          {stats.accounts.filter((account) => account.active).map((account) => (
                            <span key={account.id} className={`max-w-full truncate rounded-md px-2 py-1 text-[10px] font-medium ${style.chip}`} title={account.name}>
                              {account.name}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="grid grid-cols-3 divide-x divide-slate-100 px-2 py-3">
                        {metricOrder.map((key) => (
                          <div key={key} className="px-2 text-center">
                            <p className="text-[10px] text-slate-500">{metricLabels[key]}</p>
                            <p className="mt-1 text-sm font-semibold tabular-nums text-slate-900">{formatNumber(stats.metrics[key]?.value)}</p>
                          </div>
                        ))}
                      </div>
                      <div className="border-t border-slate-100 px-4 py-3">
                        {!stats.insights_supported && (
                          <p className="mb-2 rounded-lg bg-amber-50 px-2.5 py-2 text-[10px] leading-4 text-amber-800">
                            GHL lists posts for this network but does not provide post-level insights. Native API integration is needed for engagement metrics.
                          </p>
                        )}
                        {stats.recent_posts.length ? (
                          <ul className="space-y-2.5">
                            {stats.recent_posts.slice(0, 3).map((post) => (
                              <li key={post.id} className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <p className="line-clamp-2 text-xs leading-5 text-slate-700">{post.text || 'Published post'}</p>
                                  <time className="mt-0.5 block text-[10px] text-slate-400" dateTime={post.published_at}>
                                    {formatDate(post.published_at)}
                                  </time>
                                  {Object.keys(post.metrics).length > 0 && (
                                    <div className="mt-1.5 flex flex-wrap gap-1">
                                      {metricOrder.filter((key) => post.metrics[key] !== undefined).map((key) => (
                                        <span key={key} className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                                          {metricLabels[key]} {formatNumber(post.metrics[key])}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                                {post.permalink && (
                                  <a href={post.permalink} target="_blank" rel="noopener noreferrer" aria-label={`Open ${platformLabels[platform]} post`} className="mt-1 shrink-0 rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-indigo-700">
                                    <ArrowUpRight className="h-4 w-4" />
                                  </a>
                                )}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="py-2 text-xs text-slate-500">
                            {stats.connected_account_count
                              ? 'No published posts in this date range.'
                              : 'No connected GHL account found for this network.'}
                          </p>
                        )}
                      </div>
                    </article>
                  )
                })}
              </div>
            </section>

            <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <div className="flex items-start gap-2">
                <MessageCircle className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                <div className="space-y-1">
                  {report.notes.map((note) => (
                    <p key={note} className="text-[11px] leading-5 text-slate-500">{note}</p>
                  ))}
                </div>
              </div>
            </div>
          </>
        ) : !error ? (
          <EmptyState
            title="Social analytics are not available"
            description="We couldn’t retrieve the analytics report. Check your connection and try again."
            action={(
              <button type="button" onClick={() => void load()} className="rounded-lg bg-indigo-700 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-800">
                Retry
              </button>
            )}
          />
        ) : null}
      </div>
    </section>
  )
}

function KpiCard({
  label,
  value,
  detail,
  icon: Icon,
  tone,
}: {
  label: string
  value: string
  detail: string
  icon: typeof Activity
  tone: 'indigo' | 'emerald' | 'amber' | 'violet'
}) {
  const tones = {
    indigo: 'bg-indigo-50 text-indigo-700',
    emerald: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    violet: 'bg-violet-50 text-violet-700',
  }
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <span className={`flex h-8 w-8 items-center justify-center rounded-xl ${tones[tone]}`}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 text-2xl font-semibold tracking-tight tabular-nums text-slate-950">{value}</p>
      <p className="mt-1 text-[11px] text-slate-500">{detail}</p>
    </article>
  )
}

function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-5 py-8 text-center">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-slate-400 shadow-sm">
        <Activity className="h-5 w-5" />
      </span>
      <h4 className="mt-3 text-sm font-semibold text-slate-800">{title}</h4>
      <p className="mt-1 max-w-md text-xs leading-5 text-slate-500">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
