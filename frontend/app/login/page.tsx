// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/login/page.tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowRight, LockKeyhole, Mail, ShieldCheck, Sparkles } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const router = useRouter()

  async function handleGoogleSignIn() {
    setError(null)
    setGoogleLoading(true)

    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL
    const redirectTo = siteUrl
      ? `${siteUrl.replace(/\/+$/, '')}/auth/callback`
      : process.env.NODE_ENV === 'development'
        ? `${window.location.origin}/auth/callback`
        : null

    if (!redirectTo) {
      setError('Google sign-in is not configured for this deployment. Please contact support.')
      setGoogleLoading(false)
      return
    }

    try {
      const { error: authError } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo },
      })

      if (authError) throw authError
    } catch (cause) {
      console.error('Unable to start Google sign-in:', cause)
      setError(cause instanceof Error ? cause.message : 'Unable to start Google sign-in')
      setGoogleLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const { error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (authError) throw authError

      router.replace('/auth/callback')
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050816] px-4 py-10 text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(124,58,237,0.28),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(168,85,247,0.18),_transparent_30%)]" />
      <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] [background-size:32px_32px]" />

      <div className="relative z-10 grid w-full max-w-6xl overflow-hidden rounded-[32px] border border-white/10 bg-white/5 shadow-[0_30px_90px_rgba(91,33,182,0.45)] backdrop-blur-xl lg:grid-cols-[1.1fr_0.9fr]">
        <div className="relative hidden overflow-hidden border-r border-white/10 bg-[#0b1020] p-10 lg:flex lg:flex-col lg:justify-between">
          <div className="absolute -left-10 top-10 h-40 w-40 rounded-full bg-violet-500/30 blur-3xl" />
          <div className="absolute bottom-8 right-10 h-52 w-52 rounded-full bg-purple-600/20 blur-3xl" />

          <div className="relative z-10">
            <div className="mb-8 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-purple-700 text-lg font-black shadow-[0_0_35px_rgba(168,85,247,0.5)]">
                ENY
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.28em] text-violet-200/80">Consulting</p>
                <h1 className="text-xl font-semibold text-white">Platform</h1>
              </div>
            </div>

            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-violet-400/30 bg-violet-500/10 px-3 py-1.5 text-[10px] uppercase tracking-[0.24em] text-violet-200">
              <Sparkles className="h-3.5 w-3.5" />
              AI transformation system
            </div>

            <h2 className="max-w-md text-4xl font-black leading-tight tracking-[-0.06em] text-white">
              Build momentum across every team.
            </h2>
            <p className="mt-5 max-w-lg text-base leading-7 text-slate-300">
              One secure platform for leadership, sales, student success, marketing, operations, and day-to-day execution—powered by modern AI workflows.
            </p>
          </div>

          <div className="relative z-10 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="mb-3 flex items-center gap-2 text-violet-200">
                <ShieldCheck className="h-4 w-4" />
                <span className="text-[10px] uppercase tracking-[0.2em]">Secure</span>
              </div>
              <p className="text-sm text-slate-200">Role-based access for every team and every workflow.</p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="mb-3 flex items-center gap-2 text-violet-200">
                <Sparkles className="h-4 w-4" />
                <span className="text-[10px] uppercase tracking-[0.2em]">Smart</span>
              </div>
              <p className="text-sm text-slate-200">AI-powered dashboards, automations, and reporting.</p>
            </div>
          </div>
        </div>

        <div className="relative flex items-center justify-center p-6 sm:p-8 lg:p-12">
          <div className="w-full max-w-md">
            <div className="mb-8 text-center lg:text-left">
              <p className="text-[10px] uppercase tracking-[0.28em] text-violet-200">Welcome</p>
              <h3 className="mt-3 text-3xl font-bold text-white">Sign in or sign up</h3>
            </div>

            <button
              type="button"
              disabled={googleLoading || loading}
              onClick={handleGoogleSignIn}
              className="mb-5 inline-flex w-full items-center justify-center gap-3 rounded-2xl border border-white/15 bg-white/5 px-4 py-3.5 text-sm font-semibold text-white transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.09-1.92 3.27-4.74 3.27-8.1Z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.65l-3.57-2.77c-.99.66-2.25 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.15v2.84A11 11 0 0 0 12 23Z" />
                <path fill="#FBBC05" d="M5.84 14.11a6.6 6.6 0 0 1 0-4.22V7.05H2.15a11 11 0 0 0 0 9.9l3.69-2.84Z" />
                <path fill="#EA4335" d="M12 5.36c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.02 14.97 1 12 1a11 11 0 0 0-9.85 6.05l3.69 2.84C6.71 7.29 9.14 5.36 12 5.36Z" />
              </svg>
              {googleLoading ? 'Connecting to Google...' : 'Continue with Google'}
            </button>

            <p className="mb-5 text-center text-xs leading-5 text-slate-400">
              New Google accounts are created automatically. A CEO must assign your role before you can access the platform.
            </p>

            <div className="mb-5 flex items-center gap-3 text-xs text-slate-500">
              <div className="h-px flex-1 bg-white/10" />
              <span>or sign in with email</span>
              <div className="h-px flex-1 bg-white/10" />
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <label htmlFor="email" className="block text-sm font-medium text-slate-200">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/80 py-3 pl-10 pr-4 text-sm text-white placeholder:text-slate-500 focus:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
                    placeholder="you@enyconsulting.com"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="block text-sm font-medium text-slate-200">
                  Password
                </label>
                <div className="relative">
                  <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    id="password"
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/80 py-3 pl-10 pr-4 text-sm text-white placeholder:text-slate-500 focus:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
                    placeholder="Enter your password"
                  />
                </div>
              </div>

              {error && (
                <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || googleLoading}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-violet-500 to-purple-600 px-4 py-3.5 text-sm font-semibold text-white shadow-[0_0_30px_rgba(139,92,246,0.45)] transition hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {loading ? 'Signing in...' : 'Sign in'}
                {!loading && <ArrowRight className="h-4 w-4" />}
              </button>
            </form>

            <div className="mt-6 border-t border-white/10 pt-5 text-sm text-slate-300">
              <p>
                Need access? Contact your administrator to request access.
              </p>
              <Link href="/" className="mt-3 inline-flex items-center gap-2 text-violet-200 transition hover:text-violet-100">
                Back to home
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}