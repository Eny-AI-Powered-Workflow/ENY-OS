// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/layout.tsx
import './globals.css'
import type { Metadata } from 'next'
import { SupabaseProvider } from '@supabase/ssr'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from '@supabase/auth-helpers-react'
import { supabase } from './lib/supabaseClient'

export const metadata: Metadata = {
  title: 'ENY Consulting Platform',
  description: 'Unified AI-powered platform for ENY Consulting',
}

// Client component to handle auth redirect
'use client'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { data: session } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (session) {
      router.push('/dashboard')
    } else {
      router.push('/login')
    }
  }, [session, router])

  return (
    <html lang="en">
      <body className="antialiased">
        <SupabaseProvider supabaseClient={supabase}>
          {children}
        </SupabaseProvider>
      </body>
    </html>
  )
}