// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/CEOSignupManagement.tsx
'use client'

import { useEffect, useState } from 'react'
import { Check, RefreshCw, Users } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'

interface Account {
  id: string
  email: string | null
  full_name: string | null
  created_at: string | null
  roles: string[]
}

interface AccountDirectory {
  accounts: Account[]
  available_roles: string[]
}

function roleLabel(role: string): string {
  if (role === 'sales_lead') return 'Sales team lead'
  if (role === 'enrollment_lead') return 'Enrollment team lead'
  return role.replaceAll('_', ' ')
}

async function responseError(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data.detail === 'string') return data.detail
  } catch {
    // Use the status-based message below when the response is not JSON.
  }
  return `Request failed (${response.status})`
}

export default function CEOSignupManagement() {
  const [directory, setDirectory] = useState<AccountDirectory>({ accounts: [], available_roles: [] })
  const [selectedRoles, setSelectedRoles] = useState<Record<string, string[]>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [savingAccount, setSavingAccount] = useState<string | null>(null)

  async function loadAccounts() {
    setLoading(true)
    setError(null)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) throw new Error('Your session has expired. Please sign in again.')

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/ceo/accounts`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      if (!response.ok) throw new Error(await responseError(response))

      const data = await response.json() as AccountDirectory
      setDirectory(data)
      setSelectedRoles(Object.fromEntries(
        data.accounts.map((account) => [
          account.id,
          account.roles.filter((role) => role !== 'ceo' && data.available_roles.includes(role)),
        ]),
      ))
    } catch (cause) {
      console.error('Unable to load account directory:', cause)
      setError(cause instanceof Error ? cause.message : 'Unable to load account directory')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAccounts()
  }, [])

  function toggleRole(accountId: string, role: string) {
    setSelectedRoles((current) => {
      const currentRoles = current[accountId] ?? []
      return {
        ...current,
        [accountId]: currentRoles.includes(role)
          ? currentRoles.filter((assignedRole) => assignedRole !== role)
          : [...currentRoles, role],
      }
    })
  }

  async function saveRoles(account: Account) {
    setSavingAccount(account.id)
    setError(null)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) throw new Error('Your session has expired. Please sign in again.')

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/ceo/accounts/${account.id}/roles`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ roles: selectedRoles[account.id] ?? [] }),
        },
      )
      if (!response.ok) throw new Error(await responseError(response))

      const result = await response.json() as { id: string; roles: string[] }
      setDirectory((current) => ({
        ...current,
        accounts: current.accounts.map((item) => (
          item.id === result.id ? { ...item, roles: result.roles } : item
        )),
      }))
    } catch (cause) {
      console.error('Unable to save account roles:', cause)
      setError(cause instanceof Error ? cause.message : 'Unable to save account roles')
    } finally {
      setSavingAccount(null)
    }
  }

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-violet-200">
            <Users className="h-5 w-5" />
            <p className="text-xs font-semibold uppercase tracking-[0.18em]">Access management</p>
          </div>
          <h2 className="mt-2 text-xl font-semibold text-white">Accounts and role approvals</h2>
          <p className="mt-1 text-sm text-slate-400">
            Review Supabase accounts and assign their workspace roles. Assign a Sales or Enrollment team lead here; only team leads and the CEO can distribute leads. New accounts stay blocked until approved.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadAccounts()}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-sm text-slate-200 transition hover:border-violet-400/50 hover:bg-violet-500/10 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div role="alert" className="mt-5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      {loading ? (
        <p className="py-10 text-center text-sm text-slate-400">Loading accounts...</p>
      ) : directory.accounts.length === 0 ? (
        <p className="py-10 text-center text-sm text-slate-400">No Supabase Auth accounts were found.</p>
      ) : (
        <div className="mt-6 space-y-4">
          {directory.accounts.map((account) => {
            const assigned = account.roles.length > 0
            return (
              <article key={account.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 sm:p-5">
                <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-white">{account.full_name || account.email || 'Unnamed account'}</p>
                    <p className="mt-1 truncate text-sm text-slate-400">{account.email || 'No email address'}</p>
                    <p className={`mt-2 text-xs font-medium ${assigned ? 'text-emerald-300' : 'text-amber-200'}`}>
                      {assigned ? `Access granted: ${account.roles.map(roleLabel).join(', ')}` : 'Pending CEO role approval'}
                    </p>
                    {account.created_at && (
                      <p className="mt-1 text-xs text-slate-500">
                        Signed up {new Date(account.created_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>

                  <div className="w-full lg:max-w-2xl">
                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Assign roles</p>
                    <div className="flex flex-wrap gap-2">
                      {directory.available_roles.map((role) => {
                        const checked = (selectedRoles[account.id] ?? []).includes(role)
                        return (
                          <label
                            key={role}
                            className={`inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition ${
                              checked
                                ? 'border-violet-400/50 bg-violet-500/15 text-violet-100'
                                : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleRole(account.id, role)}
                              className="sr-only"
                            />
                            {checked && <Check className="h-3 w-3" />}
                            {roleLabel(role)}
                          </label>
                        )
                      })}
                    </div>
                    <div className="mt-4 flex justify-end">
                      <button
                        type="button"
                        onClick={() => void saveRoles(account)}
                        disabled={savingAccount === account.id}
                        className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {savingAccount === account.id ? 'Saving...' : 'Save roles'}
                      </button>
                    </div>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
