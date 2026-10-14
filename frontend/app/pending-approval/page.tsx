// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/pending-approval/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabaseClient'

export default function PendingApprovalPage() {
  const router = useRouter()
  const [signingOut, setSigningOut] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function checkAccess() {
    setChecking(true)
    setError(null)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        router.replace('/login')
        return
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      if (!response.ok) {
        throw new Error(`Unable to check account access (${response.status})`)
      }
      const data = await response.json()
      if (Array.isArray(data.roles) && data.roles.length > 0) {
        router.replace('/dashboard')
      }
    } catch (cause) {
      console.error('Unable to check account access:', cause)
      setError(cause instanceof Error ? cause.message : 'Unable to check account access')
    } finally {
      setChecking(false)
    }
  }

  async function handleSignOut() {
    setSigningOut(true)
    const { error } = await supabase.auth.signOut()
    if (error) {
      console.error('Unable to sign out:', error)
      setSigningOut(false)
      return
    }
    router.replace('/login')
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#050816] px-4 text-white">
      <div className="w-full max-w-lg rounded-3xl border border-white/10 bg-white/5 p-8 text-center shadow-2xl">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-500/15 text-xl font-bold text-violet-200">
          ENY
        </div>
        <h1 className="mt-6 text-2xl font-bold">Your account is awaiting approval</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          Your sign-in was successful. A CEO must assign your platform role before you can access the workspace.
        </p>
        {error && <p role="alert" className="mt-4 text-sm text-rose-200">{error}</p>}
        <button
          type="button"
          onClick={checkAccess}
          disabled={checking || signingOut}
          className="mt-7 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-60"
        >
          {checking ? 'Checking access...' : 'Check access again'}
        </button>
        <button
          type="button"
          onClick={handleSignOut}
          disabled={signingOut}
          className="ml-3 mt-7 rounded-xl border border-white/15 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10 disabled:opacity-60"
        >
          {signingOut ? 'Signing out...' : 'Sign out'}
        </button>
      </div>
    </main>
  )
}
