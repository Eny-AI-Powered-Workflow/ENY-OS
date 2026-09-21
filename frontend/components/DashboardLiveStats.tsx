'use client'

import { useEffect, useState } from 'react'
import { MetricCard } from '@/components/MetricCard'
import { supabase } from '@/lib/supabaseClient'
import { usePermissions } from '@/lib/permissions'

type Stats = {
  primary: { label: string; value: string | number | null; icon: string; accent: 'violet' | 'sky' | 'emerald' | 'amber' }
  secondary: { label: string; value: string | number | null; icon: string; accent: 'violet' | 'sky' | 'emerald' | 'amber' }
  tertiary: { label: string; value: string | number | null; icon: string; accent: 'violet' | 'sky' | 'emerald' | 'amber' }
  quaternary: { label: string; value: string | number | null; icon: string; accent: 'violet' | 'sky' | 'emerald' | 'amber' }
}

const initialStats: Stats = {
  primary: { label: 'Live leads', value: null, icon: '↗', accent: 'violet' },
  secondary: { label: 'Hot leads', value: null, icon: '⚡', accent: 'amber' },
  tertiary: { label: 'Pipeline value', value: null, icon: '◌', accent: 'emerald' },
  quaternary: { label: 'Completed workflows', value: null, icon: '✓', accent: 'sky' },
}

export default function DashboardLiveStats() {
  const { can, userRoles } = usePermissions()
  const [stats, setStats] = useState(initialStats)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      const { data: { session } } = await supabase.auth.getSession()
      const headers: HeadersInit = session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}
      const api = process.env.NEXT_PUBLIC_API_URL
      try {
        const [enrollment, ceo] = await Promise.all([
          can('leads:read') ? fetch(`${api}/api/v1/enrollment/metrics`, { headers, credentials: 'include' }).then((res) => res.ok ? res.json() : null) : Promise.resolve(null),
          can('pipeline:read') ? fetch(`${api}/api/v1/ceo/metrics`, { headers, credentials: 'include' }).then((res) => res.ok ? res.json() : null) : Promise.resolve(null),
        ])
        const metrics = enrollment?.metrics || {}
        const executive = ceo?.metrics || {}
        setStats({
          primary: { ...initialStats.primary, value: typeof metrics.totalLeads === 'number' ? metrics.totalLeads.toLocaleString() : null },
          secondary: { ...initialStats.secondary, value: typeof metrics.hotLeads === 'number' ? metrics.hotLeads.toLocaleString() : null },
          tertiary: { ...initialStats.tertiary, value: typeof metrics.revenuePipeline === 'number' ? `$${metrics.revenuePipeline.toLocaleString()}` : null },
          quaternary: { ...initialStats.quaternary, value: typeof executive.tasksCompleted === 'number' ? executive.tasksCompleted.toLocaleString() : null },
        })
      } catch {
        setError(true)
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [userRoles.length])

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {Object.values(stats).map((stat) => <MetricCard key={stat.label} title={stat.label} value={loading ? '—' : error ? null : stat.value} helper={error ? 'Unavailable' : 'Live from connected services'} icon={stat.icon} accent={stat.accent} />)}
    </div>
  )
}
