// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/ai-desk/page.tsx
'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Bot, CheckCircle2, ClipboardCheck, ExternalLink, MessageSquarePlus, Send, Sparkles, Trash2, UserRound, X } from 'lucide-react'
import Link from 'next/link'
import { supabase } from '@/lib/supabaseClient'

type Message = {
  role: 'user' | 'assistant'
  content: string
}

type ApiMessage = Message & { created_at?: string }

type Conversation = {
  id: string
  title: string
  updated_at?: string
}

type ContextStatus = {
  source: string
  crm_status?: string
  contacts_returned?: number
  leads_available: boolean
  scored_leads_count: number
  scored_contacts?: number
  unscored_contacts?: number
  pipeline_available: boolean
  score_distribution?: Record<string, number>
  knowledge_entries_used?: number
}

type CohortProposal = {
  status: string
  message: string
  inventory: { total_contacts: number; source_groups: Array<{ source: string; count: number }> }
  proposal: {
    cohorts?: Array<{ name: string; source: string; estimated_count: number; priority: string; reason: string; eligibility_rule: string }>
    recommended_first_batch?: { cohort_name: string; estimated_count: number; reason: string }
    human_decision?: string
    unknowns?: string[]
    raw_proposal?: string
  }
}

type BatchApproval = {
  status: string
  approval_id: string
  message: string
  cohort_name: string
  source_filter: string
  contacts: Array<{ id: string; name: string; source: string; tags: string[] }>
}

const suggestions = [
  'Give me a concise view of our highest-impact priorities this week.',
  'Turn the current lead-scoring result into a CEO action plan.',
  'Draft a decision brief with risks, options, and a recommended next move.',
]

export default function AIDeskPage() {
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [contextStatus, setContextStatus] = useState<ContextStatus | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loadingConversations, setLoadingConversations] = useState(true)
  const [cohortReview, setCohortReview] = useState<CohortProposal | null>(null)
  const [cohortLoading, setCohortLoading] = useState(false)
  const [batchApproval, setBatchApproval] = useState<BatchApproval | null>(null)
  const [batchExecution, setBatchExecution] = useState<{ status: string; processed_count?: number; failed_count?: number; approval_id?: string } | null>(null)

  const authFetch = async (path: string, options: RequestInit = {}) => {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) throw new Error('Your session has expired. Please sign in again.')
    return fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ai${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${session.access_token}`,
        ...(options.headers || {}),
      },
    })
  }

  const loadConversation = async (id: string) => {
    const response = await authFetch(`/conversation?conversation_id=${id}`)
    if (!response.ok) return
    const history: ApiMessage[] = await response.json()
    setConversationId(id)
    setMessages(history.map(({ role, content }) => ({ role, content })))
  }

  const loadConversations = async () => {
    setLoadingConversations(true)
    try {
      const response = await authFetch('/conversations')
      if (!response.ok) return
      const items: Conversation[] = await response.json()
      setConversations(items)
      if (items.length > 0) await loadConversation(items[0].id)
    } finally {
      setLoadingConversations(false)
    }
  }

  useEffect(() => {
    void loadConversations()
  }, [])

  const createConversation = async () => {
    const response = await authFetch('/conversations', { method: 'POST' })
    if (!response.ok) return
    const conversation: Conversation = await response.json()
    setConversations((current) => [conversation, ...current])
    setConversationId(conversation.id)
    setMessages([])
    setContextStatus(null)
  }

  const deleteConversation = async (id: string) => {
    const response = await authFetch(`/conversations/${id}`, { method: 'DELETE' })
    if (!response.ok) return
    const remaining = conversations.filter((conversation) => conversation.id !== id)
    setConversations(remaining)
    if (conversationId === id) {
      if (remaining[0]) await loadConversation(remaining[0].id)
      else {
        setConversationId(null)
        setMessages([])
        setContextStatus(null)
      }
    }
  }

  const reviewCohorts = async () => {
    setCohortLoading(true)
    setError(null)
    try {
      const response = await authFetch('/cohort-review', { method: 'POST', body: JSON.stringify({}) })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Cohort review could not be generated.')
      setCohortReview(payload)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Cohort review could not be generated.')
    } finally {
      setCohortLoading(false)
    }
  }

  const approveBootcampBatch = async () => {
    setCohortLoading(true)
    setError(null)
    try {
      const response = await authFetch('/cohort-batch/approve', {
        method: 'POST',
        body: JSON.stringify({ cohort_name: 'Bootcamp waitlist Batch 1', source_filter: '30-DAY CONSULTING OFFER BOOTCAMP WAITLIST', batch_size: 25 }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Batch approval failed.')
      setBatchApproval(payload)
      setBatchExecution(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Batch approval failed.')
    } finally {
      setCohortLoading(false)
    }
  }

  const executeApprovedBatch = async () => {
    if (!batchApproval?.approval_id) return
    setCohortLoading(true)
    setError(null)
    try {
      const response = await authFetch(`/cohort-batch/execute/${batchApproval.approval_id}`, { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Batch execution failed.')
      setBatchExecution({
        status: payload.status,
        processed_count: payload.processed_count,
        failed_count: payload.failed_count,
        approval_id: payload.approval_id,
      })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Batch execution failed.')
    } finally {
      setCohortLoading(false)
    }
  }

  const submitPrompt = async (event: FormEvent) => {
    event.preventDefault()
    const trimmedPrompt = prompt.trim()
    if (!trimmedPrompt || loading) return

    setMessages((current) => [...current, { role: 'user', content: trimmedPrompt }])
    setPrompt('')
    setLoading(true)
    setError(null)

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) throw new Error('Your session has expired. Please sign in again.')

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ai/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ prompt: trimmedPrompt, conversation_id: conversationId }),
      })

      if (!response.ok || !response.body) throw new Error('The AI desk could not start a response.')

      setMessages((current) => [...current, { role: 'assistant', content: '' }])
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let finished = false

      while (!finished) {
        const { value, done } = await reader.read()
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const event of events) {
          const line = event.split('\n').find((entry) => entry.startsWith('data: '))
          if (!line) continue
          const payload = JSON.parse(line.slice(6))
          if (payload.type === 'delta') {
            setMessages((current) => {
              const next = [...current]
              const last = next.length - 1
              next[last] = { role: 'assistant', content: next[last].content + payload.text }
              return next
            })
          } else if (payload.type === 'done') {
            setContextStatus(payload.business_context || null)
            setConversationId(payload.conversation_id || null)
            setConversations((current) => current.map((conversation) => conversation.id === payload.conversation_id ? { ...conversation, title: trimmedPrompt.slice(0, 42) } : conversation))
          } else if (payload.type === 'error') {
            throw new Error(payload.message)
          }
        }
        finished = done
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The AI desk could not respond.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-[1600px] min-h-[calc(100vh-9rem)] items-start gap-4">
      <aside className="sticky top-4 hidden h-[calc(100vh-10rem)] w-72 shrink-0 flex-col overflow-hidden rounded-[24px] border border-white/10 bg-slate-950/80 shadow-2xl shadow-slate-950/30 lg:flex">
        <div className="border-b border-white/10 bg-white/[0.03] p-5">
          <div className="flex items-center justify-between">
            <div><p className="text-[10px] uppercase tracking-[0.24em] text-cyan-200/70">AI Desk</p><p className="mt-1 font-semibold text-white">Conversation inbox</p></div>
            <button type="button" onClick={createConversation} aria-label="New conversation" title="New conversation" className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-300 text-slate-950 shadow-lg shadow-cyan-300/20 transition hover:bg-cyan-200"><MessageSquarePlus className="h-4 w-4" /></button>
          </div>
          <p className="mt-3 text-xs leading-5 text-slate-500">Private threads, scoped to your department context.</p>
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto p-3">
          {loadingConversations && <p className="px-3 py-4 text-xs text-slate-500">Loading history...</p>}
          {!loadingConversations && conversations.length === 0 && <p className="px-3 py-4 text-xs leading-5 text-slate-500">No conversations yet. Start a new brief.</p>}
          {conversations.map((conversation) => <div key={conversation.id} className={`group flex items-center gap-2 rounded-2xl border px-3 py-3 text-left transition ${conversation.id === conversationId ? 'border-cyan-300/30 bg-cyan-300/10 text-cyan-100' : 'border-transparent text-slate-400 hover:border-white/10 hover:bg-white/5 hover:text-white'}`}><button type="button" onClick={() => void loadConversation(conversation.id)} className="min-w-0 flex-1 truncate text-left text-xs">{conversation.title}</button><button type="button" onClick={() => void deleteConversation(conversation.id)} aria-label={`Delete ${conversation.title}`} title="Delete conversation" className="hidden shrink-0 text-slate-500 hover:text-rose-300 group-hover:block"><Trash2 className="h-3.5 w-3.5" /></button></div>)}
        </div>
      </aside>

      <main className="min-w-0 flex-1 space-y-4">
      <section className="overflow-hidden rounded-[28px] border border-cyan-300/20 bg-[radial-gradient(circle_at_top_right,_rgba(34,211,238,0.18),_transparent_35%),linear-gradient(135deg,_rgba(8,47,73,0.95),_rgba(15,23,42,0.98))] p-6 shadow-[0_24px_70px_rgba(8,47,73,0.35)] sm:p-8">
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-cyan-200">
              <Sparkles className="h-4 w-4" />
              <span className="text-[10px] uppercase tracking-[0.24em]">Role-aware intelligence</span>
            </div>
            <h1 className="mt-3 text-3xl font-black tracking-[-0.04em] text-white sm:text-4xl">ENY AI Desk</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
              Ask for analysis, decisions, drafts, and next actions. Responses are framed for your department and access level.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1.5 text-xs text-emerald-200">
            <span className="h-2 w-2 rounded-full bg-emerald-300" /> {contextStatus ? 'Live context loaded' : 'Claude ready'}
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.72fr_1.28fr]">
        <div className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Start with a brief</p>
            <h2 className="mt-2 text-xl font-semibold text-white">What needs your attention?</h2>
          </div>
          <div className="space-y-2">
            {suggestions.map((suggestion) => (
              <button key={suggestion} type="button" onClick={() => setPrompt(suggestion)} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-left text-sm leading-6 text-slate-300 transition hover:border-cyan-300/40 hover:bg-cyan-300/[0.06] hover:text-white">
                {suggestion}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => void reviewCohorts()} disabled={cohortLoading} className="flex w-full items-center justify-center gap-2 rounded-xl border border-amber-300/30 bg-amber-300/10 px-4 py-3 text-sm font-medium text-amber-100 transition hover:bg-amber-300/20 disabled:opacity-50">
            <ClipboardCheck className="h-4 w-4" /> {cohortLoading ? 'Reviewing contacts...' : 'Review lead cohorts'}
          </button>
        </div>

          <div className="flex h-[calc(100vh-19rem)] min-h-[620px] flex-col rounded-[24px] border border-white/10 bg-slate-950/60 shadow-2xl shadow-slate-950/30">
          <div className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-300/10 text-cyan-200"><Bot className="h-4 w-4" /></div>
            <div><p className="font-semibold text-white">Department copilot</p><p className="text-xs text-slate-400">Context follows your ENY role</p></div>
          </div>

          {contextStatus && <div className="border-b border-white/10 bg-cyan-300/[0.04] px-5 py-3 text-xs text-slate-400">
            {contextStatus.crm_status === 'connected' ? `GHL connected · ${contextStatus.contacts_returned || 0} contact${contextStatus.contacts_returned === 1 ? '' : 's'} checked` : 'GHL status unavailable'}
            {contextStatus.leads_available ? ` · ${contextStatus.scored_leads_count} scored lead${contextStatus.scored_leads_count === 1 ? '' : 's'}` : ' · No scored leads returned'}
                        {contextStatus.unscored_contacts ? ` · ${contextStatus.unscored_contacts} not yet scored` : ''}
            {contextStatus.pipeline_available ? ' · Pipeline context available' : ''}
            {contextStatus.knowledge_entries_used ? ` · ${contextStatus.knowledge_entries_used} ENY knowledge entr${contextStatus.knowledge_entries_used === 1 ? 'y' : 'ies'} used` : ''}
          </div>}

          <div className="flex-1 space-y-4 overflow-y-auto p-5 scrollbar-thin">
            {messages.length === 0 && <div className="flex h-full min-h-[330px] flex-col items-center justify-center text-center"><Sparkles className="h-7 w-7 text-cyan-200" /><p className="mt-4 text-sm text-slate-300">Your first brief is one prompt away.</p><p className="mt-1 max-w-sm text-xs leading-5 text-slate-500">The backend applies your authenticated department context before Claude responds.</p></div>}
            {messages.map((message, index) => <div key={`${message.role}-${index}`} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`flex max-w-[88%] gap-3 rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'bg-cyan-300 text-slate-950' : 'border border-white/10 bg-white/[0.05] text-slate-200'}`}>{message.role === 'assistant' && <Bot className="mt-1 h-4 w-4 shrink-0 text-cyan-200" />}<span className="whitespace-pre-wrap">{message.content}</span>{message.role === 'user' && <UserRound className="mt-1 h-4 w-4 shrink-0" />}</div></div>)}
            {loading && <div className="flex items-center gap-3 text-sm text-slate-400"><Bot className="h-4 w-4 text-cyan-200" /> Thinking through the brief...</div>}
          </div>

          <form onSubmit={submitPrompt} className="border-t border-white/10 p-4">
            <div className="flex items-end gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-2 focus-within:border-cyan-300/50">
              <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask your department copilot..." rows={3} className="min-h-[72px] flex-1 resize-none bg-transparent px-2 py-2 text-sm text-white outline-none placeholder:text-slate-500" />
              <button type="submit" disabled={loading || !prompt.trim()} aria-label="Send prompt" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-300 text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-40"><Send className="h-4 w-4" /></button>
            </div>
            {error && <p className="mt-3 text-xs text-rose-300">{error}</p>}
          </form>
        </div>
      </section>

    </main>

      <aside className="sticky top-4 hidden w-[360px] shrink-0 space-y-4 xl:block">
        <section className="rounded-[24px] border border-amber-300/20 bg-gradient-to-b from-amber-300/[0.10] to-slate-950/80 p-5 text-slate-200 shadow-xl shadow-slate-950/20">
          <div className="flex items-start justify-between gap-4">
            <div><p className="text-[10px] uppercase tracking-[0.22em] text-amber-200">Operations rail</p><h2 className="mt-2 text-xl font-semibold text-white">Lead cohort review</h2></div>
            <ClipboardCheck className="h-5 w-5 text-amber-200" />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-300">Review proposes. Approval authorizes. Execution changes the approved contacts.</p>
          <button type="button" onClick={() => void reviewCohorts()} disabled={cohortLoading} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl border border-amber-300/30 bg-amber-300/10 px-4 py-3 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/20 disabled:opacity-50"><ClipboardCheck className="h-4 w-4" /> {cohortLoading ? 'Reviewing contacts...' : 'Reveal lead cohort'}</button>
        </section>

        {cohortReview && <section className="max-h-[calc(100vh-18rem)] overflow-y-auto rounded-[24px] border border-amber-300/20 bg-slate-950/80 p-5 text-slate-200 shadow-xl shadow-slate-950/20">
          <div className="flex items-start justify-between gap-4"><div><p className="text-[10px] uppercase tracking-[0.2em] text-amber-200">Human review required</p><h2 className="mt-2 text-lg font-semibold text-white">Lead cohort proposal</h2></div><button type="button" onClick={() => setCohortReview(null)} aria-label="Close cohort review" title="Close cohort review" className="text-slate-400 hover:text-white"><X className="h-4 w-4" /></button></div>
          <p className="mt-3 text-xs leading-5 text-slate-400">{cohortReview.message} Inventory: {cohortReview.inventory.total_contacts} contacts.</p>
          {cohortReview.proposal.cohorts && <div className="mt-4 space-y-2">{cohortReview.proposal.cohorts.map((cohort) => <div key={`${cohort.name}-${cohort.source}`} className="rounded-xl border border-white/10 bg-white/[0.04] p-3"><div className="flex items-center justify-between gap-2"><h3 className="text-sm font-semibold text-white">{cohort.name}</h3><span className="text-[10px] uppercase tracking-[0.14em] text-amber-200">{cohort.priority}</span></div><p className="mt-1 text-xs text-slate-300">{cohort.estimated_count} contacts · {cohort.source}</p><p className="mt-2 text-xs leading-5 text-slate-500">{cohort.reason}</p></div>)}</div>}
          {cohortReview.proposal.recommended_first_batch && <div className="mt-4 rounded-xl border border-emerald-300/20 bg-emerald-300/10 p-3 text-xs"><span className="font-semibold text-emerald-100">Recommended:</span> {cohortReview.proposal.recommended_first_batch.cohort_name} ({cohortReview.proposal.recommended_first_batch.estimated_count})</div>}
          {cohortReview.proposal.human_decision && <p className="mt-4 border-t border-white/10 pt-4 text-xs leading-5 text-slate-300"><span className="font-semibold text-white">Decision owner:</span> {cohortReview.proposal.human_decision}</p>}
          <button type="button" onClick={() => void approveBootcampBatch()} disabled={cohortLoading} className="mt-5 w-full rounded-xl bg-amber-300 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-200 disabled:opacity-50">{cohortLoading ? 'Approving...' : 'Approve Bootcamp Batch 1 (25)'}</button>
        </section>}

        {batchApproval && <section className="rounded-[24px] border border-emerald-300/20 bg-emerald-300/[0.07] p-5 text-slate-200 shadow-xl shadow-slate-950/20"><div className="flex items-center gap-2 text-emerald-200"><CheckCircle2 className="h-4 w-4" /><p className="text-[10px] uppercase tracking-[0.2em]">Approved batch recorded</p></div><h2 className="mt-2 text-lg font-semibold text-white">{batchApproval.cohort_name}</h2><p className="mt-2 text-xs leading-5 text-slate-300">{batchApproval.message}</p><p className="mt-3 truncate text-[10px] text-emerald-100">Approval ID: {batchApproval.approval_id}</p><button type="button" onClick={() => void executeApprovedBatch()} disabled={cohortLoading} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-300 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-200 disabled:opacity-50">{cohortLoading ? 'Executing...' : 'Execute approved batch'}</button>{batchExecution && <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs"><div className="rounded-lg bg-slate-950/40 p-2"><span className="block text-[10px] text-slate-500">Status</span><span className="font-semibold text-white">{batchExecution.status}</span></div><div className="rounded-lg bg-slate-950/40 p-2"><span className="block text-[10px] text-slate-500">Success</span><span className="font-semibold text-emerald-200">{batchExecution.processed_count ?? 0}</span></div><div className="rounded-lg bg-slate-950/40 p-2"><span className="block text-[10px] text-slate-500">Failed</span><span className="font-semibold text-rose-200">{batchExecution.failed_count ?? 0}</span></div></div>}<Link href="/dashboard/enrollment" className="mt-4 flex items-center justify-center gap-2 text-xs text-emerald-200 hover:text-white">Open Enrollment queue <ExternalLink className="h-3 w-3" /></Link></section>}
      </aside>
    </div>
  )
}