// C:/Users/Melody/Documents/ENY-OS/frontend/components/CalendarWorkspace.tsx
'use client'

import { useCallback, useEffect, useState } from 'react'
import { CalendarDays, Clock3, RefreshCw } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'

type CalendarEvent = {
  id: string
  summary?: string
  start?: { dateTime?: string; date?: string }
  status?: string
}

type CalendarTask = {
  id: string
  title?: string
  due?: string
  status?: string
}

type Coordination = {
  calendar: { status: string; items: CalendarEvent[]; error?: string }
  tasks: { status: string; items: CalendarTask[]; error?: string }
  conflicts: Array<{ first: CalendarEvent; second: CalendarEvent }>
}

function formatDate(value?: string) {
  if (!value) return 'Date not set'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export default function CalendarWorkspace() {
  const [data, setData] = useState<Coordination | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/calendar/coordination`, {
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        credentials: 'include',
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Unable to load calendar coordination')
      }
      setData(payload)
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load calendar coordination')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-950 p-6 text-white">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Shared organization calendar</p>
          <h1 className="mt-2 text-2xl font-semibold">Calendar &amp; Tasks</h1>
          <p className="mt-2 text-sm text-slate-300">Read-only upcoming events and open Google Tasks for authorized departments.</p>
        </div>
        <button type="button" onClick={() => void load()} title="Refresh calendar and tasks" className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/5 text-slate-200 hover:bg-white/10">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </header>

      {error && <p role="alert" className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-sm text-rose-200">{error}</p>}
      {loading && !data && <p className="text-sm text-slate-300">Loading shared calendar data...</p>}
      {data && (
        <>
          <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex items-center gap-2">
                <CalendarDays className="h-5 w-5 text-cyan-700" />
                <h2 className="font-semibold text-slate-900">Upcoming events</h2>
                <span className="ml-auto text-xs text-slate-500">{data.calendar.status}</span>
              </div>
              {data.calendar.error && <p className="mt-3 text-sm text-rose-700">Calendar unavailable: {data.calendar.error}</p>}
              {data.calendar.status === 'not_configured' && <p className="mt-3 text-sm text-slate-500">Google Calendar credentials are not configured.</p>}
              <ul className="mt-4 space-y-3">
                {data.calendar.items.map((event) => (
                  <li key={event.id} className="rounded-xl bg-slate-50 p-3">
                    <p className="font-medium text-slate-900">{event.summary || 'Untitled event'}</p>
                    <p className="mt-1 flex items-center gap-2 text-xs text-slate-600">
                      <Clock3 className="h-3.5 w-3.5" />{formatDate(event.start?.dateTime || event.start?.date)}
                    </p>
                  </li>
                ))}
                {data.calendar.status === 'connected' && data.calendar.items.length === 0 && <li className="text-sm text-slate-500">No upcoming events in the next 30 days.</li>}
              </ul>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex items-center gap-2">
                <Clock3 className="h-5 w-5 text-amber-700" />
                <h2 className="font-semibold text-slate-900">Open tasks</h2>
                <span className="ml-auto text-xs text-slate-500">{data.tasks.status}</span>
              </div>
              {data.tasks.error && <p className="mt-3 text-sm text-rose-700">Tasks unavailable: {data.tasks.error}</p>}
              {data.tasks.status === 'not_configured' && <p className="mt-3 text-sm text-slate-500">Google Tasks credentials are not configured.</p>}
              <ul className="mt-4 space-y-3">
                {data.tasks.items.map((task) => (
                  <li key={task.id} className="rounded-xl bg-slate-50 p-3">
                    <p className="font-medium text-slate-900">{task.title || 'Untitled task'}</p>
                    <p className="mt-1 text-xs text-slate-600">{task.due ? `Due ${formatDate(task.due)}` : task.status || 'Open'}</p>
                  </li>
                ))}
                {data.tasks.status === 'connected' && data.tasks.items.length === 0 && <li className="text-sm text-slate-500">No open tasks.</li>}
              </ul>
            </section>
          </div>
          {data.conflicts.length > 0 && (
            <p className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 text-sm text-amber-100">
              {data.conflicts.length} event(s) share an identical start time; review the calendar for possible conflicts.
            </p>
          )}
        </>
      )}
    </div>
  )
}
