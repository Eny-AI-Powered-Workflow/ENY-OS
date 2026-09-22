'use client'

import { useEffect, useMemo, useState } from 'react'
import { MetricCard } from '@/components/MetricCard'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type Stats = {
  primary: { label: string; value: string | number | null; icon: string; accent: 'violet' | 'sky' | 'emerald' | 'amber' }
  secondary: { label: string; value: string | number | null; icon: string; accent: 'violet' | 'sky' | 'emerald' | 'amber' }
  tertiary: { label: string; value: string | number | null; icon: string; accent: 'violet' | 'sky' | 'emerald' | 'amber' }
  quaternary: { label: string; value: string | number | null; icon: string; accent: 'violet' | 'sky' | 'emerald' | 'amber' }
}

const formatNumber = (value: number | null | undefined, digits = 0) => {
  if (value === null || value === undefined || Number.isNaN(value)) return null
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value)
}

const formatCurrency = (value: number | null | undefined) => {
  if (value === null || value === undefined || Number.isNaN(value)) return null
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

const initialStats: Stats = {
  primary: { label: 'Live leads', value: null, icon: '↗', accent: 'violet' },
  secondary: { label: 'Hot leads', value: null, icon: '⚡', accent: 'amber' },
  tertiary: { label: 'Pipeline value', value: null, icon: '◌', accent: 'emerald' },
  quaternary: { label: 'Completed workflows', value: null, icon: '✓', accent: 'sky' },
}

export default function DashboardLiveStats() {
  const { permissions, can } = usePermissions()
  const [stats, setStats] = useState(initialStats)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const hasEnrollmentAccess = useMemo(() => permissions.includes('leads:read'), [permissions])
  const hasPipelineAccess = useMemo(() => permissions.includes('pipeline:read'), [permissions])

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(false)

      try {
        const { data: { session } } = await supabase.auth.getSession()
        const headers: HeadersInit = session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || (typeof window !== 'undefined' ? window.location.origin : '')

        const [enrollment, ceo] = await Promise.all([
          hasEnrollmentAccess
            ? fetch(`${baseUrl.replace(/\/$/, '')}/api/v1/enrollment/metrics`, {
                headers: {
                  ...headers,
                  Accept: 'application/json',
                },
                credentials: 'include',
              }).then((res) => (res.ok ? res.json() : null))
            : Promise.resolve(null),
          hasPipelineAccess
            ? fetch(`${baseUrl.replace(/\/$/, '')}/api/v1/ceo/metrics`, {
                headers: {
                  ...headers,
                  Accept: 'application/json',
                },
                credentials: 'include',
              }).then((res) => (res.ok ? res.json() : null))
            : Promise.resolve(null),
        ])

        const metrics = enrollment?.metrics || {}
        const executive = ceo?.metrics || {}

        setStats({
          primary: {
            ...initialStats.primary,
            value: typeof metrics.totalLeads === 'number' ? formatNumber(metrics.totalLeads) ?? '0' : null,
          },
          secondary: {
            ...initialStats.secondary,
            value: typeof metrics.hotLeads === 'number' ? formatNumber(metrics.hotLeads) ?? '0' : null,
          },
          tertiary: {
            ...initialStats.tertiary,
            value: typeof metrics.revenuePipeline === 'number' ? formatCurrency(metrics.revenuePipeline) ?? '$0' : null,
          },
          quaternary: {
            ...initialStats.quaternary,
            value: typeof executive.tasksCompleted === 'number' ? formatNumber(executive.tasksCompleted) ?? '0' : null,
          },
        })
      } catch {
        setError(true)
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [hasEnrollmentAccess, hasPipelineAccess, can])

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Object.values(stats).map((stat) => (
        <MetricCard
          key={stat.label}
          title={stat.label}
          value={loading ? '—' : error ? null : stat.value}
          helper={error ? 'Unavailable' : 'Live from connected services'}
          icon={stat.icon}
          accent={stat.accent}
        />
      ))}
    </div>
  )
}
