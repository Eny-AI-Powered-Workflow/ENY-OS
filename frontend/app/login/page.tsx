// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/login/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabaseClient'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password
      })

      if (authError) throw authError

      // Redirect to dashboard after successful login
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-primary to-primary/90">
      <div className="w-full max-w-xs space-y-6">
        <div className="flex items-center justify-center">
          <h1 className="text-2xl font-bold text-accent">ENY Platform</h1>
        </div>

        <form onSubmit={handleSubmit} className="w-full space-y-4 bg-white/10 backdrop-blur-sm rounded-xl p-8 shadow-xl">
          <div className="space-y-2">
            <label htmlFor="email" className="block text-sm font-medium text-accent mb-1">
              Email address
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-white/20 border border-white/30 rounded-lg focus:outline-none focus:ring-2 focus-ring-white/20 text-white placeholder-white/50"
              placeholder="you@enyconsulting.com"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="block text-sm font-medium text-accent mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-black/20 border border-white/30 rounded-lg focus:outline-none focus:ring-2 focus-ring-white/20 text-white placeholder-white/50"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="bg-red-500/20 text-red-500 px-4 py-2 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 btn-accent hover:bg-accent/90 transition-all font-medium"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="text-sm text-white/80">
          <p>Don't have an account? Contact your administrator to get access.</p>
          <p className="mt-2">
            <a href="/" className="underline text-accent hover:text-accent/80">
              Back to home
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}