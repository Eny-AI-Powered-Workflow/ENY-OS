// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/page.tsx
import Link from 'next/link'

const stats = [
  { value: '1 Platform', label: 'One login, multiple departments' },
  { value: '24/7', label: 'AI-powered operational coverage' },
  { value: '99.9%', label: 'Focused on reliable execution' },
]

const capabilities = [
  {
    title: 'Unified command center',
    text: 'One secure environment where sales, enrollment, student success, marketing, operations, and leadership work from a shared system of truth.',
  },
  {
    title: 'AI execution layer',
    text: 'Automate outreach, recapture lost momentum, generate reports, and power intelligent workflows with context-aware agents.',
  },
  {
    title: 'Role-based governance',
    text: 'Every team sees only what they are meant to see, with strong permission controls and audit-ready access patterns.',
  },
]

const modules = [
  //'CEO Cockpit',  // Removed the ceo cockpit for some reason sha
  'Sales & Enrollment',
  'Student Success',
  'Marketing',
  'Operations',
  'Writer & SOPs',
]

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#050816] text-white">
      <section className="relative overflow-hidden bg-[#050816]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(124,58,237,0.28),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(168,85,247,0.22),_transparent_30%)]" />
        <div className="absolute inset-0 opacity-25 [background-image:linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] [background-size:52px_52px]" />

        <div className="relative mx-auto max-w-7xl px-6 pb-20 pt-8 md:px-10 lg:px-12">
          <header className="mb-16 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-purple-700 text-lg font-black text-white shadow-[0_0_30px_rgba(168,85,247,0.55)]">
                ENY
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.28em] text-violet-200/75">Consulting</p>
                <h1 className="text-lg font-semibold text-white">Platform</h1>
              </div>
            </div>

            <nav className="hidden items-center gap-8 text-sm text-slate-300 md:flex">
              <a href="#platform" className="transition hover:text-white">Platform</a>
              <a href="#capabilities" className="transition hover:text-white">Capabilities</a>
              <a href="#modules" className="transition hover:text-white">Modules</a>
            </nav>

            <Link
              href="/login"
              className="inline-flex items-center justify-center rounded-full border border-violet-400/40 bg-violet-500/10 px-4 py-2 text-sm font-medium text-violet-100 transition hover:bg-violet-500/20"
            >
              Sign In
            </Link>
          </header>

          <div className="grid items-center gap-12 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="relative z-10">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-violet-400/30 bg-violet-500/10 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.24em] text-violet-200">
                AI transformation for modern teams
              </div>

              <h2 className="max-w-2xl text-4xl font-black leading-tight tracking-[-0.06em] text-white sm:text-5xl lg:text-7xl">
                Turn every function into a smarter operating system.
              </h2>

              <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
                ENY is the unified business platform for sales, enrollment, student outcomes, marketing, operations, and leadership—powered by AI, automation, and permission-aware workflows.
              </p>

              <div className="mt-8 flex flex-col gap-4 sm:flex-row">
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-violet-500 to-purple-600 px-6 py-3.5 text-sm font-semibold text-white shadow-[0_0_30px_rgba(139,92,246,0.55)] transition hover:scale-[1.02]"
                >
                  Get Started
                </Link>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/5 px-6 py-3.5 text-sm font-semibold text-white transition hover:border-violet-400/60 hover:bg-violet-500/10"
                >
                  Explore Dashboard
                </Link>
              </div>

              <div className="mt-10 grid gap-4 sm:grid-cols-3">
                {stats.map((item) => (
                  <div key={item.label} className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
                    <div className="text-2xl font-bold text-white">{item.value}</div>
                    <div className="mt-1 text-xs text-slate-300">{item.label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute -inset-6 rounded-[32px] bg-gradient-to-r from-violet-500/30 to-purple-500/10 blur-3xl" />
              <div className="relative overflow-hidden rounded-[32px] border border-white/10 bg-[#0b1020]/80 p-5 shadow-[0_20px_80px_rgba(91,33,182,0.45)] backdrop-blur-xl">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded-full bg-emerald-400" />
                    <span className="h-3 w-3 rounded-full bg-amber-400" />
                    <span className="h-3 w-3 rounded-full bg-rose-400" />
                  </div>
                  <span className="rounded-full border border-violet-400/30 bg-violet-500/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-violet-200">
                    live operations
                  </span>
                </div>

                <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-slate-950 to-slate-900 p-4">
                  <div className="mb-4 flex items-center justify-between">
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.24em] text-slate-400">Performance</p>
                      <h3 className="mt-1 text-xl font-semibold text-white">Executive overview</h3>
                    </div>
                    <div className="rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-300">+18.4%</div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <div className="mb-2 flex items-center justify-between text-xs text-slate-300">
                        <span>Revenue pipeline</span>
                        <span className="text-white">$425K</span>
                      </div>
                      <div className="h-2.5 overflow-hidden rounded-full bg-slate-800">
                        <div className="h-full w-[76%] rounded-full bg-gradient-to-r from-violet-500 to-purple-400" />
                      </div>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Leads</p>
                        <p className="mt-2 text-2xl font-bold text-white">1,542</p>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Conversion</p>
                        <p className="mt-2 text-2xl font-bold text-white">18.5%</p>
                      </div>
                    </div>

                    <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-3">
                      <div className="mb-2 flex items-center justify-between text-xs text-violet-100">
                        <span>AI workflow activity</span>
                        <span>96 active</span>
                      </div>
                      <div className="flex items-end gap-2">
                        {[35, 48, 60, 52, 72, 84, 96].map((height, index) => (
                          <div key={index} className="flex-1 rounded-t-lg bg-gradient-to-t from-violet-500 to-purple-300" style={{ height: `${height}px` }} />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="capabilities" className="bg-[#050816] py-24">
        <div className="mx-auto max-w-7xl px-6 md:px-10 lg:px-12">
          <div className="mb-12 max-w-2xl">
            <p className="text-[10px] uppercase tracking-[0.26em] text-violet-200">Why ENY</p>
            <h3 className="mt-3 text-3xl font-bold text-white md:text-5xl">Built for decisive, connected teams.</h3>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {capabilities.map((item) => (
              <div key={item.title} className="group rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm transition hover:-translate-y-1 hover:border-violet-400/50 hover:bg-violet-500/5">
                <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 text-lg font-bold text-white shadow-[0_0_25px_rgba(168,85,247,0.35)]">
                  •
                </div>
                <h4 className="mb-3 text-xl font-semibold text-white">{item.title}</h4>
                <p className="text-base leading-7 text-slate-300">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="modules" className="bg-[#0a0f1d] py-24">
        <div className="mx-auto max-w-7xl px-6 md:px-10 lg:px-12">
          <div className="mb-12 max-w-2xl">
            <p className="text-[10px] uppercase tracking-[0.26em] text-violet-200">Department modules</p>
            <h3 className="mt-3 text-3xl font-bold text-white md:text-5xl">Everything your business needs, in one place.</h3>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {modules.map((module, index) => (
              <div key={module} className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/5 to-white/[0.02] p-5 transition hover:border-violet-400/40 hover:bg-violet-500/5">
                <div className="mb-5 flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-violet-500/10 text-sm font-bold text-violet-200">
                    {index + 1}
                  </div>
                  <span className="text-[10px] uppercase tracking-[0.24em] text-slate-400">module</span>
                </div>
                <h4 className="text-xl font-semibold text-white">{module}</h4>
                <p className="mt-3 text-sm leading-6 text-slate-300">
                  Purpose-built workflows, clear visibility, and intelligent automation for your team’s core execution path.
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[#050816] py-24">
        <div className="mx-auto max-w-5xl px-6 text-center md:px-10 lg:px-12">
          <p className="text-[10px] uppercase tracking-[0.28em] text-violet-200">Powering growth</p>
          <h3 className="mt-4 text-3xl font-bold text-white md:text-6xl">
            Build a sharper operating rhythm.
          </h3>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-slate-300">
            From executive reporting to daily operations, ENY brings structure, clarity, and AI-driven momentum to every layer of the business.
          </p>

          <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
            <Link
              href="/login"
              className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-violet-500 to-purple-600 px-7 py-3.5 text-sm font-semibold text-white shadow-[0_0_30px_rgba(168,85,247,0.5)]"
            >
              Start now
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/5 px-7 py-3.5 text-sm font-semibold text-white"
            >
              View platform preview
            </Link>
          </div>
        </div>
      </section>
    </main>
  )
}