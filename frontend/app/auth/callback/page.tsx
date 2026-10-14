// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/auth/callback/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabaseClient'

export default function AuthCallbackPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    const completeSignIn = async () => {
      const { data: { session }, error: sessionError } = await supabase.auth.getSession()
      if (sessionError) throw sessionError
      if (!session) {
        router.replace('/login')
        return
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      if (!response.ok) {
        throw new Error(`Unable to verify account access (${response.status})`)
      }

      const data = await response.json()
      if (!Array.isArray(data.roles)) {
        throw new Error('The account roles response was invalid')
      }
      router.replace(data.roles.length > 0 ? '/dashboard' : '/pending-approval')
    }

    completeSignIn().catch((cause: unknown) => {
      console.error('Unable to complete sign-in:', cause)
      if (active) {
        setError(cause instanceof Error ? cause.message : 'Unable to complete sign-in')
      }
    })

    return () => {
      active = false
    }
  }, [router])

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#050816] px-4 text-white">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/5 p-8 text-center shadow-2xl">
        {error ? (
          <>
            <h1 className="text-xl font-semibold">Sign-in could not be completed</h1>
            <p className="mt-3 text-sm text-rose-200">{error}</p>
            <button
              type="button"
              onClick={() => router.replace('/login')}
              className="mt-6 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold hover:bg-violet-500"
            >
              Return to sign in
            </button>
          </>
        ) : (
          <>
            <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-violet-300 border-t-transparent" />
            <h1 className="text-xl font-semibold">Signing you in</h1>
            <p className="mt-2 text-sm text-slate-300">Verifying your account access...</p>
          </>
        )}
      </div>
    </main>
  )
}
