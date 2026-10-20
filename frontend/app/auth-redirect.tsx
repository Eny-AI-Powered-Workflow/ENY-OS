// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/auth-redirect.tsx
'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabaseClient'

export default function AuthRedirect() {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (pathname === '/canva/oauth-complete' || pathname === '/auth/callback') return

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (pathname === '/pending-approval') {
        if (!session) router.replace('/login')
        return
      }

      if (pathname === '/login' || pathname === '/' || pathname.startsWith('/dashboard')) {
        if (!session && pathname.startsWith('/dashboard')) {
          router.replace('/login')
          return
        }
        if (!session && pathname === '/login') {
          return
        }
        if (session && pathname.startsWith('/dashboard')) {
          void fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${session.access_token}` },
          }).then(async (response) => {
            if (response.status === 401) {
              router.replace('/login')
              return
            }
            if (!response.ok) {
              throw new Error(`Unable to verify account access (${response.status})`)
            }
            const data = await response.json()
            if (!Array.isArray(data.roles) || data.roles.length === 0) {
              router.replace('/pending-approval')
            }
          }).catch((error: unknown) => {
            console.error('Unable to verify account access:', error)
          })
        }
        return
      }

    })

    return () => subscription.unsubscribe()
  }, [pathname, router])

  return null
}