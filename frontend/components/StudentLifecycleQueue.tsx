'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ClipboardCheck, MessageSquareText } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { supabase } from '@/lib/supabaseClient';

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

export default function StudentLifecycleQueue() {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [drafts, setDrafts] = useState<DraftItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function loadLifecycleState() {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        const headers: HeadersInit = { 'Content-Type': 'application/json' }
        if (session?.access_token) {
          headers.Authorization = `Bearer ${session.access_token}`
        }

        const [queueResponse, draftResponse] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/lifecycle/queue`, {
            headers,
            credentials: 'include',
          }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/student-success/lifecycle/drafts`, {
            headers,
            credentials: 'include',
          }),
        ])

        if (!queueResponse.ok || !draftResponse.ok) {
          const queuePayload = await queueResponse.json().catch(() => ({}))
          const draftPayload = await draftResponse.json().catch(() => ({}))
          const detail = queueResponse.status === 403 || draftResponse.status === 403
            ? 'You do not have access to the lifecycle review queue.'
            : queuePayload?.detail || draftPayload?.detail || 'Lifecycle review data is unavailable.'
          throw new Error(detail)
        }

        const queueData = await queueResponse.json()
        const draftData = await draftResponse.json()

        if (!active) return
        setQueue(queueData.items ?? [])
        setDrafts(draftData.items ?? [])
      } catch (err) {
        if (active) {
          console.error('Error loading lifecycle queue:', err)
          setError(err instanceof Error ? err.message : 'Lifecycle queue is unavailable.')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadLifecycleState()
    return () => { active = false }
  }, [])

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <ClipboardCheck className="h-5 w-5 text-muted-foreground mr-2" />
          <CardTitle className="text-sm">Loading lifecycle queue...</CardTitle>
        </CardHeader>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader className="flex flex-col items-center py-6">
          <AlertTriangle className="h-5 w-5 text-amber-600 mr-2" />
          <CardTitle className="text-sm text-amber-700">Lifecycle queue unavailable</CardTitle>
          <p className="text-center text-sm text-muted-foreground">{error}</p>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center gap-2">
          <ClipboardCheck className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Student lifecycle work queue</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Human-reviewed follow-up only. No message is sent or action taken without staff approval.
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {queue.map((item) => (
            <div key={item.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-slate-900">{item.label}</span>
                <span className="rounded-full bg-slate-200 px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-slate-700">
                  {item.status}
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-700">{item.summary}</p>
              <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
                <span>Owner: {item.owner}</span>
                <span>{item.manual_review_required ? 'Manual review' : 'Auto-queue'}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-center gap-2">
            <MessageSquareText className="h-4 w-4 text-amber-700" />
            <h3 className="text-sm font-semibold text-amber-900">Draft communication review</h3>
          </div>
          {drafts.length === 0 ? (
            <p className="mt-3 text-sm text-amber-800">No draft reminders or check-ins are queued yet.</p>
          ) : (
            <div className="mt-3 space-y-3">
              {drafts.map((draft) => (
                <div key={draft.id} className="rounded border border-amber-200 bg-white p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-slate-900">{draft.student_name}</span>
                    <span className="rounded-full bg-amber-100 px-2 py-1 text-[10px] uppercase tracking-wide text-amber-800">
                      {draft.status}
                    </span>
                  </div>
                  <p className="mt-2 text-xs uppercase tracking-wide text-slate-500">{draft.category}</p>
                  <p className="mt-2 text-sm text-slate-700">{draft.message}</p>
                  <p className="mt-2 text-[11px] text-slate-500">
                    {draft.requires_human_approval ? 'Review required before any send action.' : 'Ready for staff review.'}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
