// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/ai-desk/page.tsx
'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Bot, CheckCircle2, ClipboardCheck, Clock3, Database, ExternalLink, ImagePlus, LoaderCircle, MessageSquarePlus, Save, Send, ShieldCheck, Sparkles, Trash2, UserRound, WandSparkles, Workflow, X } from 'lucide-react'
import Link from 'next/link'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { visit } from 'unist-util-visit'
import type { PhrasingContent, Root, Strong } from 'mdast'
import type { Properties } from 'hast'
import type { Plugin } from 'unified'
import { usePermissions } from '@/lib/permissions'
import { supabase } from '@/lib/supabaseClient'
import { describeHttpError, describeRequestFailure } from '@/lib/api'

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
  contacts_accessible?: boolean
  contacts_returned?: number
  leads_available: boolean
  scored_leads_count: number
  scored_contacts?: number
  unscored_contacts?: number
  pipeline_available: boolean
  score_distribution?: Record<string, number>
  knowledge_entries_used?: number
  active_knowledge_document_count?: number
}

type CapabilitySnapshot = {
  user: { display_name: string; roles: string[] }
  as_of: string
  integrations: Array<{ id: string; name: string; status: string; access: string; permission: string }>
  features: { can_assess_creative: boolean; can_propose_workflows: boolean; can_approve_workflows: boolean; can_execute_workflows: boolean; can_view_platform_metrics: boolean }
  available_workflows: Array<{ key: string; name: string; owner: string; mode: string; description: string; requires_human_approval: boolean }>
}

type ActionProposal = {
  id: string
  workflow_name: string
  summary: string
  payload: Record<string, unknown>
  status: 'pending' | 'approved' | 'executing' | 'rejected' | 'executed' | 'failed' | 'expired'
  expires_at: string
  created_at?: string
  executed_at?: string
  execution_result?: { status: string; message: string; workflow?: string } | null
}

type DesignAssessment = {
  overall_score: number
  verdict: string
  summary: string
  strengths: string[]
  risks: string[]
  criteria: Array<{ name: string; score: number; feedback: string }>
  recommendations: string[]
  accessibility_checks: string[]
  evidence: string[]
  sources: Array<{ title: string; version?: number; type: string }>
  reviewed_at: string
  review_scope: string
}

type CreativeImageType = 'image/jpeg' | 'image/png' | 'image/webp'

function isCreativeImageType(mediaType: string): mediaType is CreativeImageType {
  return mediaType === 'image/jpeg' || mediaType === 'image/png' || mediaType === 'image/webp'
}

type CohortProposal = {
  status: string
  message: string
  inventory: { total_contacts: number; source_groups: Array<{ source: string; count: number; unscored_count?: number }> }
  proposal: {
    cohorts?: Array<{ name: string; source: string; estimated_count: number; priority: string; reason: string; eligibility_rule: string }>
    recommended_first_batch?: { cohort_name: string; source?: string; estimated_count: number; reason: string }
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

type PendingIntakeLead = {
  contact_id: string
  name: string
  email: string | null
  phone: string | null
  source: string
  received_at: string | null
  ghl_available: boolean
}

const roleSuggestions: Record<string, string[]> = {
  ceo: [
    "Prepare an executive brief of this week's most important decisions and risks.",
    'Compare our top priorities and recommend where leadership attention will have the greatest impact.',
    'Draft a concise action plan for improving organizational performance this week.',
  ],
  programs_manager: [
    'Summarize learner progress and identify the program issues that need my attention first.',
    'Recommend practical interventions for learners who may be falling behind.',
    'Build a weekly program operations checklist from the most urgent open work.',
  ],
  customer_success: [
    'Help me prioritize learner follow-ups based on urgency and likely impact.',
    'Draft a supportive check-in for a learner who has stopped making progress.',
    'Suggest next steps for resolving a learner support issue while keeping their experience positive.',
  ],
  business_support: [
    'Summarize the client and contract work that should be prioritized this week.',
    'Draft a clear client update about a pending business support request.',
    'Identify the key risks and follow-up actions in a business support pilot review.',
  ],
  executive_assistant: [
    'Prepare a concise executive briefing with decisions, deadlines, and follow-ups.',
    'Turn these meeting notes into an owner-based action list for the leadership team.',
    'Research the options for an upcoming executive decision and summarize the trade-offs.',
  ],
  enrollment: [
    'Help me prioritize lead follow-ups by readiness, urgency, and next best action.',
    'Draft a personalized first-touch message for a prospective student.',
    'Suggest ways to re-engage leads who have not responded to recent outreach.',
  ],
  marketing: [
    'Suggest content ideas that fit our current campaign goals and audience.',
    'Review these marketing results and recommend one practical optimization.',
    'Draft a channel-specific post that supports this week’s marketing focus.',
  ],
  marketing_lead: [
    'Summarize campaign performance and flag approvals or decisions needed from me.',
    'Recommend how to balance this week’s content calendar across our active campaigns.',
    'Review a campaign plan for audience fit, brand risks, and measurable outcomes.',
  ],
  videographer: [
    'Help me prioritize the video production queue and identify likely delivery blockers.',
    'Turn this video brief into a practical shoot-day checklist.',
    'Suggest an editing and publishing plan for this video deliverable.',
  ],
  graphic_designer: [
    'Turn this design request into a clear creative brief with deliverables and constraints.',
    'Suggest visual directions for a funnel page that fits the target audience and goal.',
    'Review this creative concept for brand consistency, clarity, and conversion opportunities.',
  ],
  developer: [
    'Help me triage this platform issue into likely causes and safe diagnostic steps.',
    'Review this implementation plan for integration risks and missing edge cases.',
    'Suggest a focused test plan for verifying a workflow change without disrupting users.',
  ],
}

const fallbackSuggestions = [
  'Help me identify the most important priorities for my team this week.',
  'Turn this work request into a clear plan with owners and next steps.',
  'Review this decision and summarize the options, risks, and recommendation.',
]

function getRoleSuggestions(roles: string[]): string[] {
  const role = roles.find((assignedRole) => roleSuggestions[assignedRole])
  return (role && roleSuggestions[role]) || fallbackSuggestions
}

declare module 'mdast' {
  interface Data {
    hName?: string
    hProperties?: Properties
  }
}

const remarkHighlight: Plugin<[], Root> = () => (tree) => {
  visit(tree, 'text', (node, index, parent) => {
    if (index === undefined || !parent) return

    const parts = node.value.split(/==(.*?)==/g)
    if (parts.length === 1) return

    const replacement: PhrasingContent[] = []
    parts.forEach((part, partIndex) => {
      if (!part) return
      if (partIndex % 2 === 0) {
        replacement.push({ type: 'text', value: part })
        return
      }

      const highlight: Strong = {
        type: 'strong',
        data: {
          hName: 'mark',
          hProperties: { className: ['rounded', 'bg-amber-300/20', 'px-1', 'text-amber-100'] },
        },
        children: [{ type: 'text', value: part }],
      }
      replacement.push(highlight)
    })

    parent.children.splice(index, 1, ...replacement)
    return index + replacement.length
  })
}

const assistantMarkdownComponents: Components = {
  h1: ({ children }) => <h1 className="mb-3 mt-5 text-xl font-bold tracking-tight text-white first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-2.5 mt-5 border-b border-white/10 pb-2 text-lg font-semibold text-white">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-2 mt-4 text-base font-semibold text-cyan-100">{children}</h3>,
  p: ({ children }) => <p className="my-2.5 leading-7 text-slate-200">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
  em: ({ children }) => <em className="italic text-slate-100">{children}</em>,
  mark: ({ children }) => <mark className="rounded bg-amber-300/20 px-1 text-amber-100">{children}</mark>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-6 marker:text-cyan-300">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-6 marker:font-semibold marker:text-cyan-200">{children}</ol>,
  li: ({ children }) => <li className="pl-1 leading-6 text-slate-200">{children}</li>,
  blockquote: ({ children }) => <blockquote className="my-4 border-l-2 border-cyan-300/50 pl-4 text-slate-300">{children}</blockquote>,
  a: ({ children, href }) => <a href={href} className="font-medium text-cyan-200 underline decoration-cyan-200/40 underline-offset-4 hover:text-cyan-100">{children}</a>,
  hr: () => <hr className="my-5 border-white/10" />,
  pre: ({ children }) => <pre className="my-4 overflow-x-auto rounded-xl border border-white/10 bg-slate-950/80 p-4 text-xs leading-6 text-slate-200">{children}</pre>,
  code: ({ children, className }) => (
    <code className={className
      ? 'font-mono text-[0.85em] text-cyan-100'
      : 'rounded-md border border-white/10 bg-slate-950/70 px-1.5 py-0.5 font-mono text-[0.85em] text-cyan-100'}
    >
      {children}
    </code>
  ),
  table: ({ children }) => <div className="my-4 overflow-x-auto rounded-xl border border-white/10"><table className="w-full border-collapse text-left text-xs">{children}</table></div>,
  th: ({ children }) => <th className="border-b border-white/10 bg-white/5 px-3 py-2 font-semibold text-white">{children}</th>,
  td: ({ children }) => <td className="border-b border-white/5 px-3 py-2 align-top text-slate-300">{children}</td>,
}

function formatApiError(detail: unknown, fallback: string): string {
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (typeof detail === 'object') {
    const value = detail as {
      message?: string
      requested_source?: string
      available_sources?: string[]
      unscored_sample_count?: number
    }
    const parts = [value.message || fallback]
    if (value.requested_source) parts.push(`Requested source: ${value.requested_source}`)
    if (value.available_sources?.length) parts.push(`Available GHL sources: ${value.available_sources.join(', ')}`)
    if (value.unscored_sample_count !== undefined) parts.push(`Unscored sample available: ${value.unscored_sample_count}`)
    return parts.join(' · ')
  }
  return fallback
}

/** Parse a response body without throwing on empty, HTML or invalid payloads. */
async function readApiPayload<T>(response: Response): Promise<T | null> {
  try {
    const raw = await response.text()
    if (!raw) return null
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

export default function AIDeskPage() {
  const { userRoles } = usePermissions()
  const suggestions = getRoleSuggestions(userRoles)
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
  const [pendingIntake, setPendingIntake] = useState<PendingIntakeLead[]>([])
  const [selectedIntakeIds, setSelectedIntakeIds] = useState<string[]>([])
  const [capabilities, setCapabilities] = useState<CapabilitySnapshot | null>(null)
  const [memoryDraft, setMemoryDraft] = useState({
    response_style: '',
    focus_areas: '',
    working_hours: '',
    decision_preferences: '',
  })
  const [memorySaving, setMemorySaving] = useState(false)
  const [memorySaved, setMemorySaved] = useState(false)
  const [actionIntent, setActionIntent] = useState('')
  const [actionNotice, setActionNotice] = useState('')
  const [actionProposals, setActionProposals] = useState<ActionProposal[]>([])
  const [actionLoading, setActionLoading] = useState(false)
  const [designAssessmentInput, setDesignAssessmentInput] = useState({
    title: '',
    audience: 'marketing',
    channel: 'social',
    brief: '',
    goals: '',
  })
  const [designAssessment, setDesignAssessment] = useState<DesignAssessment | null>(null)
  const [designAssessmentLoading, setDesignAssessmentLoading] = useState(false)
  const [creativeImage, setCreativeImage] = useState<{ data: string; mediaType: CreativeImageType; name: string } | null>(null)
  const [localTime, setLocalTime] = useState('')

  const authFetch = async (path: string, options: RequestInit = {}) => {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) throw new Error('Your session has expired. Please sign in again.')
    try {
      return await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ai${path}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
          ...(options.headers || {}),
        },
      })
    } catch (error) {
      throw new Error(describeRequestFailure(error, 'The AI desk could not reach the API.'))
    }
  }

  const loadPendingIntake = async () => {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) return
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/intake/pending`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      credentials: 'include',
    })
    if (!response.ok) throw new Error(await describeHttpError(response, 'Unable to load incoming GHL leads.'))
    const payload = await response.json()
    const leads: PendingIntakeLead[] = payload.leads || []
    setPendingIntake(leads)
    setSelectedIntakeIds((selected) => selected.filter((id) => leads.some((lead) => lead.contact_id === id)))
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

  const loadAssistantCapabilities = async () => {
    const response = await authFetch('/assistant/capabilities')
    if (!response.ok) throw new Error(await describeHttpError(response, 'Unable to load available AI tools.'))
    const payload: CapabilitySnapshot = await response.json()
    setCapabilities(payload)
  }

  const loadAssistantMemory = async () => {
    const response = await authFetch('/assistant/memory')
    if (!response.ok) throw new Error(await describeHttpError(response, 'Unable to load your AI preferences.'))
    const payload = await response.json()
    setMemoryDraft({
      response_style: payload.preferences?.response_style || '',
      focus_areas: (payload.preferences?.focus_areas || []).join(', '),
      working_hours: payload.preferences?.working_hours || '',
      decision_preferences: payload.preferences?.decision_preferences || '',
    })
  }

  const loadActionProposals = async () => {
    const response = await authFetch('/assistant/action-proposals')
    if (!response.ok) throw new Error(await describeHttpError(response, 'Unable to load workflow proposals.'))
    const payload = await response.json()
    setActionProposals(payload.proposals || [])
  }

  useEffect(() => {
    void Promise.all([
      loadAssistantCapabilities(),
      loadAssistantMemory(),
    ]).catch((caught) => setError(caught instanceof Error ? caught.message : 'Unable to load AI assistant settings.'))
  }, [])

  useEffect(() => {
    if (!capabilities?.features.can_approve_workflows) return
    void loadActionProposals().catch((caught) => setError(caught instanceof Error ? caught.message : 'Unable to load workflow proposals.'))
  }, [capabilities?.features.can_approve_workflows])

  useEffect(() => {
    const refreshClock = () => {
      setLocalTime(new Intl.DateTimeFormat(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      }).format(new Date()))
    }
    refreshClock()
    const interval = window.setInterval(refreshClock, 60_000)
    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!userRoles.some((role) => ['ceo', 'enrollment', 'sales'].includes(role))) return
    void loadPendingIntake().catch((caught) => setError(caught instanceof Error ? caught.message : 'Unable to load incoming GHL leads.'))
    const interval = window.setInterval(() => {
      void loadPendingIntake().catch((caught) => setError(caught instanceof Error ? caught.message : 'Unable to refresh incoming GHL leads.'))
    }, 60_000)
    return () => window.clearInterval(interval)
  }, [userRoles])

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
      if (!response.ok) throw new Error(formatApiError(payload.detail, 'Cohort review could not be generated.'))
      setCohortReview(payload)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Cohort review could not be generated.')
    } finally {
      setCohortLoading(false)
    }
  }

  const approveCohortBatch = async (cohort: { name: string; source: string; estimated_count: number }) => {
    setCohortLoading(true)
    setError(null)
    try {
      const response = await authFetch('/cohort-batch/approve', {
        method: 'POST',
        body: JSON.stringify({
          cohort_name: `${cohort.name} Batch 1`,
          source_filter: cohort.source,
          batch_size: Math.min(25, Math.max(1, cohort.estimated_count)),
        }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(formatApiError(payload.detail, 'Batch approval failed.'))
      setBatchApproval(payload)
      setBatchExecution(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Batch approval failed.')
    } finally {
      setCohortLoading(false)
    }
  }

  const approveIncomingBatch = async () => {
    const chosen = pendingIntake.filter((lead) => selectedIntakeIds.includes(lead.contact_id)).slice(0, 25)
    if (!chosen.length) return
    setCohortLoading(true)
    setError(null)
    try {
      const response = await authFetch('/cohort-batch/approve', {
        method: 'POST',
        body: JSON.stringify({
          cohort_name: `GHL inbound batch ${new Date().toISOString().slice(0, 10)}`,
          source_filter: 'GHL inbound review',
          batch_size: chosen.length,
          contact_ids: chosen.map((lead) => lead.contact_id),
        }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(formatApiError(payload.detail, 'Batch approval failed.'))
      setBatchApproval(payload)
      setBatchExecution(null)
      setSelectedIntakeIds([])
      await loadPendingIntake()
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
      if (!response.ok) throw new Error(formatApiError(payload.detail, 'Batch execution failed.'))
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

    const saveAssistantMemory = async (event: FormEvent) => {
      event.preventDefault()
      setMemorySaving(true)
      setMemorySaved(false)
      setError(null)
      try {
        const response = await authFetch('/assistant/memory', {
          method: 'PUT',
          body: JSON.stringify({
            preferences: {
              response_style: memoryDraft.response_style,
              focus_areas: memoryDraft.focus_areas.split(',').map((item) => item.trim()).filter(Boolean).slice(0, 5),
              working_hours: memoryDraft.working_hours,
              decision_preferences: memoryDraft.decision_preferences,
            },
          }),
        })
        if (!response.ok) throw new Error(await describeHttpError(response, 'Your AI preferences could not be saved.'))
        setMemorySaved(true)
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Your AI preferences could not be saved.')
      } finally {
        setMemorySaving(false)
      }
    }

    const prepareWorkflowProposal = async (event: FormEvent) => {
      event.preventDefault()
      if (!actionIntent.trim() || actionLoading) return
      setActionLoading(true)
      setError(null)
      try {
        const response = await authFetch('/assistant/action-proposals', {
          method: 'POST',
          body: JSON.stringify({ intent: actionIntent.trim() }),
        })
        const payload: ActionProposal = await response.json()
        if (!response.ok) throw new Error(formatApiError(payload, 'The assistant could not prepare a workflow proposal.'))
        setActionProposals((current) => [payload, ...current])
        setActionIntent('')
        setActionNotice('Proposal created. The authorized workflow owner can review it for 30 minutes.')
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'The assistant could not prepare a workflow proposal.')
      } finally {
        setActionLoading(false)
      }
    }

    const decideWorkflowProposal = async (proposal: ActionProposal, decision: 'approve' | 'reject') => {
      setActionLoading(true)
      setError(null)
      try {
        const response = await authFetch(`/assistant/action-proposals/${proposal.id}/decision`, {
          method: 'POST',
          body: JSON.stringify({ decision }),
        })
        const updated: ActionProposal = await response.json()
        if (!response.ok) throw new Error(formatApiError(updated, 'The proposal could not be updated.'))
        setActionProposals((current) => current.map((item) => item.id === updated.id ? updated : item))
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'The proposal could not be updated.')
      } finally {
        setActionLoading(false)
      }
    }

    const executeWorkflowProposal = async (proposal: ActionProposal) => {
      setActionLoading(true)
      setError(null)
      try {
        const response = await authFetch(`/assistant/action-proposals/${proposal.id}/execute`, { method: 'POST' })
        const payload = await response.json()
        if (!response.ok) throw new Error(formatApiError(payload, 'The approved workflow could not be executed.'))
        setActionProposals((current) => current.map((item) => item.id === proposal.id ? payload.proposal : item))
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'The approved workflow could not be executed.')
        void loadActionProposals()
      } finally {
        setActionLoading(false)
      }
    }

    const assessCreative = async (event: FormEvent) => {
      event.preventDefault()
      setDesignAssessmentLoading(true)
      setDesignAssessment(null)
      setError(null)
      try {
        const response = await authFetch('/assistant/design-assessment', {
          method: 'POST',
          body: JSON.stringify({
            ...designAssessmentInput,
            goals: designAssessmentInput.goals.split(',').map((item) => item.trim()).filter(Boolean).slice(0, 10),
            image_base64: creativeImage?.data,
            image_media_type: creativeImage?.mediaType,
          }),
        })
        const payload: DesignAssessment = await response.json()
        if (!response.ok) throw new Error(formatApiError(payload, 'Creative assessment could not be completed.'))
        setDesignAssessment(payload)
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Creative assessment could not be completed.')
      } finally {
        setDesignAssessmentLoading(false)
      }
    }

    const selectCreativeImage = (file: File | undefined) => {
      setCreativeImage(null)
      if (!file) return
      setError(null)
      if (file.size > 5 * 1024 * 1024) {
        setError('Creative images must be 5 MB or smaller.')
        return
      }
      const mediaType = file.type
      if (!isCreativeImageType(mediaType)) {
        setError('Choose a JPEG, PNG, or WebP creative image.')
        return
      }
      const reader = new FileReader()
      reader.onerror = () => setError('The selected creative image could not be read.')
      reader.onload = () => {
        if (typeof reader.result !== 'string') {
          setError('The selected creative image could not be read.')
          return
        }
        const encoded = reader.result.split(',')[1]
        if (!encoded) {
          setError('The selected creative image could not be encoded.')
          return
        }
        setCreativeImage({ data: encoded, mediaType, name: file.name })
      }
      reader.readAsDataURL(file)
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
        body: JSON.stringify({
          prompt: trimmedPrompt,
          conversation_id: conversationId,
          timezone_name: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
        }),
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
    <div className="mx-auto flex min-h-[calc(100vh-9rem)] w-full min-w-0 max-w-[1600px] items-start gap-4">
      <aside className="sticky top-4 hidden h-[calc(100vh-10rem)] w-60 shrink-0 flex-col overflow-hidden rounded-[24px] border border-white/10 bg-slate-950/80 shadow-2xl shadow-slate-950/30 lg:flex xl:w-64">
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
        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-white/10 pt-4 text-xs text-slate-300">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/40 px-3 py-1.5">
            <UserRound className="h-3.5 w-3.5 text-cyan-200" />
            Personalized for {capabilities?.user.display_name || 'your account'}
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/40 px-3 py-1.5">
            <Clock3 className="h-3.5 w-3.5 text-cyan-200" />
            {localTime || 'Checking local time…'}
          </span>
          <span className="rounded-full border border-white/10 bg-slate-950/40 px-3 py-1.5">
            {capabilities?.user.roles.join(' · ') || userRoles.join(' · ') || 'Role context loading'}
          </span>
        </div>
      </section>

      <section className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)]">
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
          {capabilities && <section className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
            <div className="flex items-center gap-2 text-cyan-100">
              <Database className="h-4 w-4" />
              <h3 className="text-sm font-semibold text-white">Your connected context</h3>
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-500">Access is checked by the backend for every request. This shows configuration and role permissions, not live health or source data included in this chat.</p>
            <div className="mt-3 space-y-2">
              {capabilities.integrations.map((integration) => <div key={integration.id} className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-xs font-medium text-slate-200">{integration.name}</p>
                  <p className="truncate text-[10px] text-slate-500">{integration.access.replaceAll('_', ' ')}</p>
                </div>
                <span className={`shrink-0 rounded-full px-2 py-1 text-[9px] uppercase tracking-wide ${integration.status === 'available' || integration.status === 'configured' ? 'bg-emerald-300/10 text-emerald-200' : integration.status === 'restricted' ? 'bg-amber-300/10 text-amber-200' : 'bg-slate-700/60 text-slate-400'}`}>{integration.status.replaceAll('_', ' ')}</span>
              </div>)}
            </div>
          </section>}
          <section className="rounded-2xl border border-cyan-300/15 bg-cyan-300/[0.04] p-4">
            <div className="flex items-center justify-between gap-2">
              <div><p className="text-[10px] uppercase tracking-[0.2em] text-cyan-200">Private to your account</p><h3 className="mt-1 text-sm font-semibold text-white">Assistant preferences</h3></div>
              <ShieldCheck className="h-4 w-4 text-cyan-200" />
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-500">Optional preferences help shape responses. Your verified name and role come from your account.</p>
            <form onSubmit={saveAssistantMemory} className="mt-3 space-y-2.5">
              <label className="block text-[10px] text-slate-400">Preferred response style
                <input value={memoryDraft.response_style} onChange={(event) => setMemoryDraft((current) => ({ ...current, response_style: event.target.value }))} maxLength={160} placeholder="Concise, with clear recommendations" className="mt-1 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2 text-xs text-white outline-none focus:border-cyan-300/50" />
              </label>
              <label className="block text-[10px] text-slate-400">Focus areas (comma separated)
                <input value={memoryDraft.focus_areas} onChange={(event) => setMemoryDraft((current) => ({ ...current, focus_areas: event.target.value }))} maxLength={620} placeholder="Student outcomes, team priorities" className="mt-1 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2 text-xs text-white outline-none focus:border-cyan-300/50" />
              </label>
              <label className="block text-[10px] text-slate-400">Working hours
                <input value={memoryDraft.working_hours} onChange={(event) => setMemoryDraft((current) => ({ ...current, working_hours: event.target.value }))} maxLength={300} placeholder="Weekdays, 9:00–17:00" className="mt-1 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2 text-xs text-white outline-none focus:border-cyan-300/50" />
              </label>
              <label className="block text-[10px] text-slate-400">Decision preferences
                <textarea value={memoryDraft.decision_preferences} onChange={(event) => setMemoryDraft((current) => ({ ...current, decision_preferences: event.target.value }))} maxLength={300} rows={2} placeholder="Show trade-offs and flag assumptions" className="mt-1 w-full resize-y rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2 text-xs text-white outline-none focus:border-cyan-300/50" />
              </label>
              <button type="submit" disabled={memorySaving} className="flex w-full items-center justify-center gap-2 rounded-xl border border-cyan-300/20 bg-cyan-300/10 px-3 py-2.5 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-300/15 disabled:opacity-50">
                {memorySaving ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                {memorySaving ? 'Saving preferences…' : memorySaved ? 'Preferences saved' : 'Save my preferences'}
              </button>
            </form>
          </section>
          {capabilities?.features.can_assess_creative && <section className="rounded-2xl border border-fuchsia-300/20 bg-fuchsia-300/[0.04] p-4">
            <div className="flex items-center gap-2 text-fuchsia-100">
              <WandSparkles className="h-4 w-4" />
              <h3 className="text-sm font-semibold text-white">Creative assessment</h3>
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-500">Assess a written brief and optional design image against approved standards available to your role. Images are sent to Claude for assessment and are not stored by ENY or published; remove personal or confidential details first.</p>
            <form onSubmit={assessCreative} className="mt-3 space-y-2.5">
              <input required minLength={2} value={designAssessmentInput.title} onChange={(event) => setDesignAssessmentInput((current) => ({ ...current, title: event.target.value }))} placeholder="Creative title" className="w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2 text-xs text-white outline-none focus:border-fuchsia-300/50" />
              <div className="grid grid-cols-2 gap-2">
                <select value={designAssessmentInput.audience} onChange={(event) => setDesignAssessmentInput((current) => ({ ...current, audience: event.target.value }))} className="rounded-lg border border-white/10 bg-slate-950 px-2 py-2 text-xs text-white">
                  <option value="marketing">Marketing</option><option value="programs">Programs</option><option value="student_success">Student success</option><option value="shared">Shared</option>
                </select>
                <input required value={designAssessmentInput.channel} onChange={(event) => setDesignAssessmentInput((current) => ({ ...current, channel: event.target.value }))} placeholder="Channel" className="min-w-0 rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2 text-xs text-white outline-none focus:border-fuchsia-300/50" />
              </div>
              <input value={designAssessmentInput.goals} onChange={(event) => setDesignAssessmentInput((current) => ({ ...current, goals: event.target.value }))} placeholder="Goals (comma separated)" className="w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2 text-xs text-white outline-none focus:border-fuchsia-300/50" />
              <textarea required minLength={20} maxLength={12000} rows={5} value={designAssessmentInput.brief} onChange={(event) => setDesignAssessmentInput((current) => ({ ...current, brief: event.target.value }))} placeholder="Paste the written concept, message, or creative brief…" className="w-full resize-y rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2 text-xs leading-5 text-white outline-none focus:border-fuchsia-300/50" />
              <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-fuchsia-300/20 bg-slate-950/50 px-3 py-2.5 text-xs text-slate-300">
                <ImagePlus className="h-4 w-4 shrink-0 text-fuchsia-200" />
                <span className="min-w-0 flex-1">{creativeImage ? `${creativeImage.name} · ${creativeImage.mediaType}` : 'Add design image (JPEG, PNG, WebP; up to 5 MB)'}</span>
                <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(event) => selectCreativeImage(event.currentTarget.files?.[0])} />
              </label>
              {creativeImage && <button type="button" onClick={() => setCreativeImage(null)} className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-white"><X className="h-3 w-3" />Remove image</button>}
              <button type="submit" disabled={designAssessmentLoading} className="flex w-full items-center justify-center gap-2 rounded-xl bg-fuchsia-300 px-3 py-2.5 text-xs font-semibold text-slate-950 transition hover:bg-fuchsia-200 disabled:opacity-50">
                {designAssessmentLoading ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <WandSparkles className="h-3.5 w-3.5" />}
                {designAssessmentLoading ? 'Assessing…' : 'Assess creative'}
              </button>
            </form>
            {designAssessment && <div className="mt-4 space-y-3 rounded-xl border border-fuchsia-300/15 bg-slate-950/60 p-3">
              <div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold text-white">{designAssessment.verdict.replaceAll('_', ' ')}</span><span className="rounded-full bg-fuchsia-300/10 px-2 py-1 text-xs font-semibold text-fuchsia-100">{designAssessment.overall_score}/100</span></div>
              <p className="text-xs leading-5 text-slate-300">{designAssessment.summary}</p>
              <div className="space-y-2">{designAssessment.criteria.map((criterion) => <div key={criterion.name} className="rounded-lg bg-white/[0.03] p-2"><div className="flex justify-between gap-2 text-[10px]"><span className="font-medium text-slate-200">{criterion.name}</span><span className="text-cyan-200">{criterion.score}/100</span></div><p className="mt-1 text-[10px] leading-4 text-slate-400">{criterion.feedback}</p></div>)}</div>
              {designAssessment.recommendations.length > 0 && <div><p className="text-[10px] font-semibold uppercase tracking-wide text-fuchsia-100">Next improvements</p><ul className="mt-1 list-disc space-y-1 pl-4 text-[10px] leading-4 text-slate-300">{designAssessment.recommendations.map((recommendation, index) => <li key={`${recommendation}-${index}`}>{recommendation}</li>)}</ul></div>}
              <p className="text-[9px] leading-4 text-slate-500">{designAssessment.review_scope}</p>
            </div>}
          </section>}
          {(capabilities?.features.can_propose_workflows || capabilities?.features.can_approve_workflows) && <section className="rounded-2xl border border-emerald-300/20 bg-emerald-300/[0.04] p-4">
            <div className="flex items-center gap-2 text-emerald-100">
              <Workflow className="h-4 w-4" />
              <h3 className="text-sm font-semibold text-white">Approved workflow actions</h3>
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-500">Claude can prepare a proposal for an allowlisted draft/review workflow. It cannot execute until a workflow owner approves the exact request; publishing workflows are excluded here.</p>
            {capabilities.features.can_propose_workflows && <form onSubmit={prepareWorkflowProposal} className="mt-3 space-y-2">
              <textarea required minLength={10} maxLength={4000} value={actionIntent} onChange={(event) => setActionIntent(event.target.value)} rows={3} placeholder="Describe the workflow task you want prepared for review…" className="w-full resize-y rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2 text-xs leading-5 text-white outline-none focus:border-emerald-300/50" />
              <button type="submit" disabled={actionLoading || !actionIntent.trim()} className="flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-300/20 bg-emerald-300/10 px-3 py-2.5 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-300/15 disabled:opacity-50">
                {actionLoading ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                {actionLoading ? 'Preparing…' : 'Prepare a proposal'}
              </button>
            </form>}
            {actionNotice && <p role="status" className="mt-2 text-[10px] leading-4 text-emerald-100">{actionNotice}</p>}
            {capabilities.features.can_approve_workflows && <div className="mt-3 space-y-2">
              {actionProposals.map((proposal) => <article key={proposal.id} className="rounded-xl border border-white/10 bg-slate-950/70 p-3">
                <div className="flex items-start justify-between gap-2"><div><p className="text-[9px] uppercase tracking-wider text-emerald-200">{proposal.workflow_name.replaceAll('-', ' ')}</p><p className="mt-1 text-xs font-medium text-white">{proposal.summary}</p></div><span className={`shrink-0 rounded-full px-2 py-1 text-[9px] uppercase ${proposal.status === 'executed' ? 'bg-emerald-300/10 text-emerald-200' : proposal.status === 'pending' || proposal.status === 'approved' ? 'bg-amber-300/10 text-amber-100' : 'bg-slate-700/60 text-slate-400'}`}>{proposal.status}</span></div>
                <pre className="mt-2 max-h-24 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/20 p-2 text-[9px] leading-4 text-slate-400">{JSON.stringify(proposal.payload, null, 2)}</pre>
                <p className="mt-2 text-[9px] text-slate-500">Expires {new Date(proposal.expires_at).toLocaleString()}</p>
                {(userRoles.includes('ceo') || capabilities.available_workflows.some((workflow) => workflow.key === proposal.workflow_name)) && proposal.status === 'pending' && <div className="mt-2 grid grid-cols-2 gap-2"><button type="button" disabled={actionLoading} onClick={() => void decideWorkflowProposal(proposal, 'approve')} className="rounded-lg bg-emerald-300 px-2 py-2 text-[10px] font-semibold text-slate-950 disabled:opacity-50">Approve this exact proposal</button><button type="button" disabled={actionLoading} onClick={() => void decideWorkflowProposal(proposal, 'reject')} className="rounded-lg border border-white/10 px-2 py-2 text-[10px] font-medium text-slate-300 disabled:opacity-50">Reject</button></div>}
                {capabilities.features.can_execute_workflows && (userRoles.includes('ceo') || capabilities.available_workflows.some((workflow) => workflow.key === proposal.workflow_name)) && proposal.status === 'approved' && <button type="button" disabled={actionLoading} onClick={() => void executeWorkflowProposal(proposal)} className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-300 px-2 py-2 text-[10px] font-semibold text-slate-950 disabled:opacity-50"><Workflow className="h-3 w-3" />Execute approved workflow</button>}
                {proposal.execution_result && <p className="mt-2 text-[10px] leading-4 text-slate-300">Execution {proposal.execution_result.status}: {proposal.execution_result.message}</p>}
              </article>)}
              {actionProposals.length === 0 && <p className="rounded-lg border border-dashed border-white/10 p-3 text-[10px] text-slate-500">No workflow proposals yet.</p>}
            </div>}
          </section>}
          {userRoles.some((role) => ['ceo', 'enrollment', 'sales'].includes(role)) && <section className="rounded-2xl border border-cyan-300/20 bg-cyan-300/[0.05] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-200">GHL intake · human approval required</p>
                <h3 className="mt-1 text-sm font-semibold text-white">Incoming leads</h3>
              </div>
              <span className="rounded-full bg-cyan-300/10 px-2 py-1 text-xs font-semibold text-cyan-100">{pendingIntake.length}</span>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-400">New GHL contacts wait here for the team to approve a batch. Nothing is scored or messaged on arrival.</p>
            {pendingIntake.length > 0 && <div className="mt-3 max-h-64 space-y-2 overflow-y-auto">
              {pendingIntake.map((lead) => <label key={lead.contact_id} className="flex cursor-pointer items-start gap-2 rounded-xl border border-white/10 bg-slate-950/50 p-3 text-xs">
                <input type="checkbox" checked={selectedIntakeIds.includes(lead.contact_id)} onChange={(event) => setSelectedIntakeIds((selected) => event.target.checked
                  ? selected.length < 25 ? [...selected, lead.contact_id] : selected
                  : selected.filter((id) => id !== lead.contact_id))} className="mt-0.5 accent-cyan-300" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold text-white">{lead.name || lead.contact_id}</span>
                  <span className="mt-1 block truncate text-slate-400">{lead.email || lead.phone || 'No contact channel'} · {lead.source}</span>
                  {!lead.ghl_available && <span className="mt-1 block text-amber-200">Contact could not be loaded from GHL</span>}
                </span>
              </label>)}
            </div>}
            {pendingIntake.length > 0 && <button type="button" onClick={() => void approveIncomingBatch()} disabled={!selectedIntakeIds.length || cohortLoading || pendingIntake.some((lead) => selectedIntakeIds.includes(lead.contact_id) && !lead.ghl_available)} className="mt-3 w-full rounded-xl bg-cyan-300 px-3 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-50">
              {cohortLoading ? 'Creating approved batch...' : `Approve selected (${selectedIntakeIds.length}/25)`}
            </button>}
          </section>}
          <button type="button" onClick={() => void reviewCohorts()} disabled={cohortLoading} className="flex w-full items-center justify-center gap-2 rounded-xl border border-amber-300/30 bg-amber-300/10 px-4 py-3 text-sm font-medium text-amber-100 transition hover:bg-amber-300/20 disabled:opacity-50">
            <ClipboardCheck className="h-4 w-4" /> {cohortLoading ? 'Reviewing contacts...' : 'Review lead cohorts'}
          </button>
        </div>

          <div className="flex h-[calc(100vh-18rem)] min-h-[420px] min-w-0 flex-col rounded-[24px] border border-white/10 bg-slate-950/60 shadow-2xl shadow-slate-950/30">
          <div className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-300/10 text-cyan-200"><Bot className="h-4 w-4" /></div>
            <div><p className="font-semibold text-white">Department copilot</p><p className="text-xs text-slate-400">Context follows your ENY role</p></div>
          </div>

          {contextStatus && <div className="border-b border-white/10 bg-cyan-300/[0.04] px-5 py-3 text-xs text-slate-400">
            {!contextStatus.crm_status ? 'CRM data was not included in this role-scoped response' : contextStatus.crm_status === 'connected' ? `GHL connected${contextStatus.contacts_accessible ? ` · ${contextStatus.contacts_returned || 0} contacts checked` : ' · contact records are not in this context'}` : contextStatus.crm_status === 'not_configured' ? 'GHL is not configured' : 'GHL contact context unavailable'}
            {contextStatus.contacts_accessible && (contextStatus.leads_available ? ` · ${contextStatus.scored_leads_count} scored lead${contextStatus.scored_leads_count === 1 ? '' : 's'}` : ' · No scored leads returned')}
                        {contextStatus.unscored_contacts ? ` · ${contextStatus.unscored_contacts} not yet scored` : ''}
            {contextStatus.pipeline_available ? ' · Pipeline context available' : ''}
            {contextStatus.knowledge_entries_used ? ` · ${contextStatus.knowledge_entries_used} ENY knowledge entr${contextStatus.knowledge_entries_used === 1 ? 'y' : 'ies'} used` : ''}
            {contextStatus.active_knowledge_document_count !== undefined ? ` · ${contextStatus.active_knowledge_document_count} active knowledge documents visible` : ''}
          </div>}

          <div className="flex-1 space-y-4 overflow-y-auto p-5 scrollbar-thin">
            {messages.length === 0 && <div className="flex h-full min-h-[330px] flex-col items-center justify-center text-center"><Sparkles className="h-7 w-7 text-cyan-200" /><p className="mt-4 text-sm text-slate-300">Your first brief is one prompt away.</p><p className="mt-1 max-w-sm text-xs leading-5 text-slate-500">The backend applies your authenticated department context before Claude responds.</p></div>}
            {messages.map((message, index) => <div key={`${message.role}-${index}`} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`flex min-w-0 max-w-[88%] gap-3 rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'bg-cyan-300 text-slate-950' : 'border border-white/10 bg-white/[0.05] text-slate-200'}`}>{message.role === 'assistant' && <Bot className="mt-1 h-4 w-4 shrink-0 text-cyan-200" />}{message.role === 'assistant' ? <div className="min-w-0 flex-1 overflow-hidden"><ReactMarkdown remarkPlugins={[remarkGfm, remarkHighlight]} components={assistantMarkdownComponents}>{message.content}</ReactMarkdown></div> : <span className="whitespace-pre-wrap">{message.content}</span>}{message.role === 'user' && <UserRound className="mt-1 h-4 w-4 shrink-0" />}</div></div>)}
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

      <aside className="sticky top-4 hidden w-80 shrink-0 space-y-4 2xl:block">
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
          {cohortReview.proposal.cohorts && <div className="mt-4 space-y-2">{cohortReview.proposal.cohorts.map((cohort) => <div key={`${cohort.name}-${cohort.source}`} className="rounded-xl border border-white/10 bg-white/[0.04] p-3"><div className="flex items-center justify-between gap-2"><h3 className="text-sm font-semibold text-white">{cohort.name}</h3><span className={`text-[10px] uppercase tracking-[0.14em] ${cohort.priority === 'hold' ? 'text-slate-500' : 'text-amber-200'}`}>{cohort.priority}</span></div><p className="mt-1 text-xs text-slate-300">{cohort.estimated_count} unscored contacts · {cohort.source}</p><p className="mt-2 text-xs leading-5 text-slate-500">{cohort.reason}</p></div>)}</div>}
          {cohortReview.proposal.recommended_first_batch && <div className="mt-4 rounded-xl border border-emerald-300/20 bg-emerald-300/10 p-3 text-xs"><span className="font-semibold text-emerald-100">Recommended:</span> {cohortReview.proposal.recommended_first_batch.cohort_name} ({cohortReview.proposal.recommended_first_batch.estimated_count})</div>}
          {cohortReview.proposal.human_decision && <p className="mt-4 border-t border-white/10 pt-4 text-xs leading-5 text-slate-300"><span className="font-semibold text-white">Decision owner:</span> {cohortReview.proposal.human_decision}</p>}
          {cohortReview.proposal.cohorts && <div className="mt-5 space-y-2">{cohortReview.proposal.cohorts.map((cohort) => <button key={`approve-${cohort.name}-${cohort.source}`} type="button" onClick={() => void approveCohortBatch(cohort)} disabled={cohortLoading || cohort.priority === 'hold'} className="flex w-full items-center justify-between rounded-xl bg-amber-300 px-4 py-3 text-left text-sm font-semibold text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-50"><span>{cohortLoading ? 'Approving...' : `Approve ${cohort.name}`}</span><span className="text-xs font-normal">up to {Math.min(25, cohort.estimated_count)}</span></button>)}</div>}
        </section>}

        {batchApproval && <section className="rounded-[24px] border border-emerald-300/20 bg-emerald-300/[0.07] p-5 text-slate-200 shadow-xl shadow-slate-950/20"><div className="flex items-center gap-2 text-emerald-200"><CheckCircle2 className="h-4 w-4" /><p className="text-[10px] uppercase tracking-[0.2em]">Approved batch recorded</p></div><h2 className="mt-2 text-lg font-semibold text-white">{batchApproval.cohort_name}</h2><p className="mt-2 text-xs leading-5 text-slate-300">{batchApproval.message}</p><p className="mt-3 truncate text-[10px] text-emerald-100">Approval ID: {batchApproval.approval_id}</p><button type="button" onClick={() => void executeApprovedBatch()} disabled={cohortLoading} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-300 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-200 disabled:opacity-50">{cohortLoading ? 'Executing...' : 'Execute approved batch'}</button>{batchExecution && <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs"><div className="rounded-lg bg-slate-950/40 p-2"><span className="block text-[10px] text-slate-500">Status</span><span className="font-semibold text-white">{batchExecution.status}</span></div><div className="rounded-lg bg-slate-950/40 p-2"><span className="block text-[10px] text-slate-500">Success</span><span className="font-semibold text-emerald-200">{batchExecution.processed_count ?? 0}</span></div><div className="rounded-lg bg-slate-950/40 p-2"><span className="block text-[10px] text-slate-500">Failed</span><span className="font-semibold text-rose-200">{batchExecution.failed_count ?? 0}</span></div></div>}<Link href="/dashboard/enrollment" className="mt-4 flex items-center justify-center gap-2 text-xs text-emerald-200 hover:text-white">Open Enrollment queue <ExternalLink className="h-3 w-3" /></Link></section>}
      </aside>
    </div>
  )
}
