// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/page.tsx
import type { Metadata } from 'next'
import Link from 'next/link'
import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  BriefcaseBusiness,
  ClipboardList,
  GraduationCap,
  Megaphone,
  ShieldCheck,
  Sparkles,
  Users,
  type LucideIcon,
} from 'lucide-react'

export const metadata: Metadata = {
  title: 'ENY OS | Internal platform',
  description: 'The internal workspace for ENY Consulting Inc.',
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    title: 'ENY OS | Internal platform',
    description: 'One workspace for how ENY runs.',
    siteName: 'ENY OS',
    type: 'website',
  },
}

const capabilities = [
  {
    icon: BookOpen,
    title: 'A clearer view of the work',
    text: 'Bring day-to-day workflows into one place, so teams spend less time switching tools and reconciling updates.',
  },
  {
    icon: Sparkles,
    title: 'AI assistance in the workflow',
    text: 'Use AI-supported tools for practical work such as drafting, research, and reporting, without losing team context.',
  },
  {
    icon: ShieldCheck,
    title: 'Access that matches your role',
    text: 'Workspace access is tied to assigned permissions. Teams see the tools made available to their account.',
  },
]

const modules: {
  title: string
  description: string
  href: string
  icon: LucideIcon
}[] = [
  {
    title: 'Leadership',
    description: 'Review executive metrics, team activity, and operational health.',
    href: '/dashboard/ceo',
    icon: BriefcaseBusiness,
  },
  {
    title: 'Sales & Enrollment',
    description: 'Work the lead pipeline, review prospects, and coordinate follow-up.',
    href: '/dashboard/enrollment',
    icon: Users,
  },
  {
    title: 'Student Success',
    description: 'Review student records, progress, payments, and support queues.',
    href: '/dashboard/student-success',
    icon: GraduationCap,
  },
  {
    title: 'Marketing',
    description: 'Coordinate campaign content, performance, and marketing activity.',
    href: '/dashboard/marketing',
    icon: Megaphone,
  },
  {
    title: 'Operations',
    description: 'Review operational metrics, system status, and recent tasks.',
    href: '/dashboard/operations',
    icon: ClipboardList,
  },
  {
    title: 'Writer & SOPs',
    description: 'Create and manage documents, standard procedures, and templates.',
    href: '/dashboard/writer',
    icon: BookOpen,
  },
]

const principles = [
  'One login for ENY teams',
  'Role-based access to workspaces',
  'AI assistance in daily workflows',
]

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#f6f5f1] text-[#17263b]">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-[#142238]/95 text-white backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/" aria-label="ENY OS home" className="group flex items-center gap-3 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#e2b75e]">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#e2b75e] text-sm font-bold tracking-tight text-[#142238]">ENY</span>
            <span>
              <span className="block text-lg font-semibold tracking-tight">ENY OS</span>
              <span className="block text-xs text-slate-300">Consulting</span>
            </span>
          </Link>

          <nav aria-label="Main navigation" className="flex items-center gap-5">
            <a href="#workspaces" className="hidden rounded text-sm text-slate-200 transition hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#e2b75e] sm:inline">
              Workspaces
            </a>
            <Link
              href="/login"
              className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-[#e2b75e] px-4 text-sm font-semibold text-[#142238] transition hover:bg-[#f0ca79] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"
            >
              Sign in <ArrowUpRight aria-hidden="true" className="h-4 w-4" />
            </Link>
          </nav>
        </div>
      </header>

      <section aria-labelledby="hero-title" className="relative overflow-hidden bg-[#142238] text-white">
        <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-[42%] border-l border-white/[0.06] lg:block" />
        <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 py-16 sm:px-8 sm:py-20 lg:grid-cols-[1.05fr_0.95fr] lg:py-24">
          <div className="relative z-10">
            <p className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-[#f0ca79]">
              <span className="h-2 w-2 rounded-full bg-[#e2b75e]" />
              Internal platform · ENY Consulting Inc.
            </p>
            <h1 id="hero-title" className="max-w-2xl font-serif text-5xl leading-[1.08] tracking-tight sm:text-6xl lg:text-7xl">
              One workspace for how ENY runs.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-200">
              Sales, enrollment, student success, marketing, and operations in one workspace, with AI assistance and access shaped by your role.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/login"
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-[#e2b75e] px-5 text-sm font-semibold text-[#142238] transition hover:bg-[#f0ca79] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"
              >
                Sign in with your ENY account <ArrowRight aria-hidden="true" className="h-4 w-4" />
              </Link>
              <a
                href="#workspaces"
                className="inline-flex min-h-12 items-center justify-center rounded-lg border border-white/25 px-5 text-sm font-semibold text-white transition hover:border-white/60 hover:bg-white/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#e2b75e]"
              >
                See what’s inside
              </a>
            </div>
          </div>

          <div aria-label="Illustrative ENY OS workspace interface, with no live business data" className="relative mx-auto w-full max-w-xl">
            <div className="overflow-hidden rounded-xl border border-white/15 bg-[#f6f5f1] text-[#17263b] shadow-2xl shadow-black/20">
              <div className="flex items-center justify-between border-b border-[#dfe2e5] px-5 py-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#526176]">ENY OS workspace</p>
                  <p className="mt-1 text-sm font-semibold">Your work, in one place</p>
                </div>
                <span className="rounded-full border border-[#dfe2e5] bg-white px-3 py-1 text-xs text-[#526176]">Illustrative preview</span>
              </div>
              <div className="grid min-h-[290px] sm:grid-cols-[175px_1fr]">
                <div className="border-b border-[#dfe2e5] bg-[#eeefeb] p-3 sm:border-b-0 sm:border-r">
                  <p className="px-2 pb-2 pt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#68778a]">Workspaces</p>
                  {modules.slice(0, 4).map((module, index) => {
                    const Icon = module.icon
                    return (
                      <div key={module.title} className={`flex items-center gap-2 rounded-md px-2 py-2 text-xs ${index === 0 ? 'bg-white font-semibold text-[#17263b] shadow-sm' : 'text-[#526176]'}`}>
                        <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />
                        {module.title}
                      </div>
                    )
                  })}
                </div>
                <div className="p-5 sm:p-6">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-medium text-[#59697d]">Leadership</p>
                      <p className="mt-1 text-xl font-semibold tracking-tight">Executive overview</p>
                    </div>
                    <BarChart3 aria-hidden="true" className="h-5 w-5 text-[#9a742b]" />
                  </div>
                  <div className="mt-6 space-y-3">
                    {['Team activity', 'Pipeline review', 'Operational health'].map((item, index) => (
                      <div key={item} className="flex items-center justify-between rounded-lg border border-[#dfe2e5] bg-white px-3 py-3">
                        <span className="flex items-center gap-3 text-sm font-medium">
                          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-[#f3ead5] text-xs font-semibold text-[#765719]">0{index + 1}</span>
                          {item}
                        </span>
                        <ArrowUpRight aria-hidden="true" className="h-4 w-4 text-[#59697d]" />
                      </div>
                    ))}
                  </div>
                  <p className="mt-4 text-xs leading-5 text-[#59697d]">Illustrative interface only. No live account or business data is shown.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section aria-label="Platform principles" className="border-b border-[#e2e3df] bg-white">
        <div className="mx-auto grid max-w-7xl gap-4 px-5 py-6 sm:grid-cols-3 sm:px-8">
          {principles.map((principle) => (
            <p key={principle} className="flex items-center gap-3 text-sm font-medium text-[#33445a]">
              <ShieldCheck aria-hidden="true" className="h-5 w-5 shrink-0 text-[#9a742b]" />
              {principle}
            </p>
          ))}
        </div>
      </section>

      <section id="why-eny" aria-labelledby="why-title" className="scroll-mt-24 py-20 sm:py-24">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <div className="mb-10 max-w-2xl">
            <p className="text-sm font-semibold text-[#8a6827]">Why ENY OS</p>
            <h2 id="why-title" className="mt-3 font-serif text-4xl leading-tight tracking-tight sm:text-5xl">
              Less switching. Clearer work.
            </h2>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {capabilities.map((item) => {
              const Icon = item.icon
              return (
                <article key={item.title} className="rounded-xl border border-[#e0e2df] bg-white p-6">
                  <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-[#f3ead5] text-[#765719]">
                    <Icon aria-hidden="true" className="h-5 w-5" />
                  </span>
                  <h3 className="mt-5 text-lg font-semibold tracking-tight">{item.title}</h3>
                  <p className="mt-3 text-base leading-7 text-[#526176]">{item.text}</p>
                </article>
              )
            })}
          </div>
        </div>
      </section>

      <section id="workspaces" aria-labelledby="workspaces-title" className="scroll-mt-24 border-y border-[#e2e3df] bg-white py-20 sm:py-24">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="max-w-2xl">
              <p className="text-sm font-semibold text-[#8a6827]">Inside ENY OS</p>
              <h2 id="workspaces-title" className="mt-3 font-serif text-4xl leading-tight tracking-tight sm:text-5xl">
                Workspaces for the work ENY does.
              </h2>
            </div>
            <p className="max-w-md text-base leading-7 text-[#526176]">
              Sign in to see the areas available to your account. Access depends on your assigned role.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {modules.map((module) => {
              const Icon = module.icon
              return (
                <Link
                  key={module.title}
                  href={module.href}
                  className="group flex min-h-48 flex-col rounded-xl border border-[#e0e2df] bg-[#fbfbf9] p-5 transition hover:-translate-y-0.5 hover:border-[#c7ab6f] hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#9a742b]"
                >
                  <div className="flex items-start justify-between">
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f3ead5] text-[#765719]">
                      <Icon aria-hidden="true" className="h-5 w-5" />
                    </span>
                    <span className="rounded-full border border-[#d9dedf] px-2.5 py-1 text-xs font-medium text-[#526176]">Role access</span>
                  </div>
                  <h3 className="mt-5 text-lg font-semibold tracking-tight">{module.title}</h3>
                  <p className="mt-2 flex-1 text-base leading-6 text-[#526176]">{module.description}</p>
                  <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-[#765719]">
                    Sign in to open <ArrowUpRight aria-hidden="true" className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </span>
                </Link>
              )
            })}
          </div>
          <p className="mt-5 text-sm leading-6 text-[#59697d]">
            Workspace descriptions reflect the current application areas. The tools and information available after sign-in depend on assigned permissions.
          </p>
        </div>
      </section>

      <footer className="bg-[#142238] py-10 text-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <div>
            <p className="font-semibold">Need access or help?</p>
            <p className="mt-1 text-sm text-slate-300">Contact your ENY platform administrator.</p>
          </div>
          <div className="flex flex-col gap-2 text-sm text-slate-300 sm:items-end">
            <p>Internal use only · ENY Consulting Inc.</p>
            <Link href="/login" className="inline-flex min-h-10 items-center gap-2 font-semibold text-[#f0ca79] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#e2b75e]">
              Sign in <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </footer>
    </main>
  )
}
