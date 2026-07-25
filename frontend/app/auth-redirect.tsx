// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/auth-redirect.tsx
'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabaseClient'

export default function AuthRedirect() {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      // Don't redirect on login or dashboard pages to avoid infinite loops
      if (pathname === '/login' || pathname === '/dashboard') {
        return
      }

      if (session) {
        router.push('/dashboard')
      } else {
        router.push('/login')
      }
    })

    return () => subscription.unsubscribe()
  }, [pathname, router])

  return null
}