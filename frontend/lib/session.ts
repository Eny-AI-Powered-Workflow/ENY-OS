// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/lib/session.ts
import { useState, useEffect } from 'react'
import { supabase } from './supabaseClient'
import { User } from '@supabase/supabase-js'

export function useSession() {
  const [session, setSession] = useSessionState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    // Listen for auth changes
    const {
      data: { subscription }
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [])

  return { session, loading }
}

function useState<T>(initialState: T | (() => T)) {
  return useState(initialState)
}