// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/enrollment-operations/page.tsx
import { redirect } from 'next/navigation'

type Operation = {
  id: string
  contact_id: string
  contact_name: string | null
  email: string | null
  source: string | null
  score: number | null
  queue_status: string
  follow_up_status: string
  assigned_user_id: string | null
  execution_status: string
  error: string | null
  retry_count: number
  created_at: string | null
}

type OperationsPayload = {
  summary: Record<string, number>
  results: Operation[]
  audit_events: Array<{ id: string; event_type: string; result_id: string | null; created_at: string | null }>
}

const statusStyles: Record<string, string> = {
  new: 'bg-slate-100 text-slate-700',
  assigned: 'bg-amber-100 text-amber-800',
  contacted: 'bg-cyan-100 text-cyan-800',
  qualified: 'bg-emerald-100 text-emerald-800',
  closed: 'bg-slate-200 text-slate-600',
}

export default function EnrollmentOperationsPage() {
  redirect('/dashboard/enrollment/lead-operations')
}
