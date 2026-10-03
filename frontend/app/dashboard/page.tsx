'use client'

import Link from 'next/link'
import {
  ArrowUpRight,
  BriefcaseBusiness,
  ClipboardList,
  GraduationCap,
  Megaphone,
  Monitor,
  Palette,
  Pencil,
  Settings,
  Sparkles,
  Video,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { MODULES, usePermissions } from '@/lib/permissions'

const moduleIcons: Record<string, LucideIcon> = {
  Monitor,
  Users,
  GraduationCap,
  ClipboardList,
  Megaphone,
  Video,
  Palette,
  Settings,
  Pencil,
  Sparkles,
  BriefcaseBusiness,
}

const moduleDescriptions: Record<string, string> = {
  '/dashboard/ceo': 'Review executive metrics, team activity, and operational health.',
  '/dashboard/enrollment': 'Work the lead pipeline, review qualified prospects, and manage follow-up.',
  '/dashboard/student-success': 'Review learner records, attendance, payments, and support queues.',
  '/dashboard/business-support': 'Manage business support requests, contracts, and client work.',
  '/dashboard/marketing': 'Plan campaigns, review performance, and coordinate content.',
  '/dashboard/videographer': 'Manage video production tasks, uploads, and publishing workflows.',
  '/dashboard/designer': 'Create and review design work, templates, and funnel assets.',
  '/dashboard/operations': 'Monitor platform operations, workflows, and service health.',
  '/dashboard/writer': 'Create documents, manage SOPs, and work with writing agents.',
  '/dashboard/ai-desk': 'Use the role-scoped AI assistant for day-to-day work.',
  '/dashboard/executive-assistant': 'Review executive briefings, research, and assistant workflows.',
}

const cardAccents = [
  { bar: 'bg-violet-400', icon: 'border-violet-400/20 bg-violet-400/10 text-violet-200' },
  { bar: 'bg-cyan-400', icon: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-200' },
  { bar: 'bg-emerald-400', icon: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200' },
  { bar: 'bg-amber-400', icon: 'border-amber-400/20 bg-amber-400/10 text-amber-200' },
  { bar: 'bg-rose-400', icon: 'border-rose-400/20 bg-rose-400/10 text-rose-200' },
] as const

const formatRole = (role: string) => role
  .split('_')
  .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
  .join(' ')

export default function DashboardPage() {
  const { canAll, userRoles } = usePermissions()
  const accessibleModules = MODULES.filter((module) => module.permissions.length === 0
    ? userRoles.includes('ceo')
    : canAll(module.permissions))
  const primaryRole = userRoles[0] ? formatRole(userRoles[0]) : null

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-3xl border border-slate-800 bg-[radial-gradient(ellipse_at_top_left,_rgba(124,58,237,0.2),_transparent_45%),linear-gradient(130deg,_#111827_0%,_#0b1723_55%,_#10252c_100%)] p-6 shadow-[0_24px_60px_rgba(15,23,42,0.35)] sm:p-8">
        <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-cyan-400/5 blur-3xl" />
        <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase text-cyan-200">ENY workspace</p>
            <h1 className="mt-3 text-3xl font-bold text-white sm:text-4xl">
              {primaryRole ? `Welcome back, ${primaryRole}.` : 'Welcome to ENY.'}
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300 sm:text-base">
              Your starting point for the tools and workflows enabled for your account.
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-3 self-start rounded-xl border border-white/10 bg-slate-950/40 px-4 py-3 md:self-auto">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-400/10 text-cyan-200">
              <BriefcaseBusiness className="h-4 w-4" />
            </span>
            <div>
              <p className="text-lg font-semibold text-white">{accessibleModules.length}</p>
              <p className="text-xs text-slate-400">Available workspaces</p>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="workspaces-heading" className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 id="workspaces-heading" className="text-xl font-semibold text-white">Your workspaces</h2>
            <p className="mt-1 text-sm text-slate-400">Available according to your assigned access.</p>
          </div>
          {primaryRole && <span className="hidden rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-300 sm:inline-flex">{primaryRole}</span>}
        </div>

        {accessibleModules.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {accessibleModules.map((module, index) => {
              const Icon = moduleIcons[module.icon] || BriefcaseBusiness
              const accent = cardAccents[index % cardAccents.length]

              return (
                <Link key={module.href} href={module.href} className="group block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950">
                  <article className="relative h-full min-h-52 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70 p-5 transition duration-200 group-hover:-translate-y-1 group-hover:border-slate-600 group-hover:bg-slate-900">
                    <div className={`absolute inset-x-0 top-0 h-1 ${accent.bar}`} />
                    <div className="flex items-start justify-between gap-4">
                      <span className={`flex h-11 w-11 items-center justify-center rounded-xl border ${accent.icon}`}>
                        <Icon className="h-5 w-5" />
                      </span>
                      <ArrowUpRight className="h-4 w-4 text-slate-500 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-white" />
                    </div>
                    <h3 className="mt-5 text-lg font-semibold text-white">{module.name}</h3>
                    <p className="mt-2 min-h-10 text-sm leading-5 text-slate-400">
                      {moduleDescriptions[module.href] || 'Open the tools and workflows available in this workspace.'}
                    </p>
                    <p className="mt-5 text-xs font-medium text-slate-300">Open workspace</p>
                  </article>
                </Link>
              )
            })}
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 text-sm text-slate-300">
            No workspaces are currently enabled for this account. Contact your platform administrator if you need access.
          </div>
        )}
      </section>

      <section aria-label="Account guidance" className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-slate-800 bg-slate-900/55 p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-400/20 bg-emerald-400/10 text-emerald-200">
              <Settings className="h-4 w-4" />
            </span>
            <div>
              <h2 className="font-semibold text-white">Access at a glance</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                {primaryRole
                  ? `Your ${primaryRole} role currently opens ${accessibleModules.length} ${accessibleModules.length === 1 ? 'workspace' : 'workspaces'} in ENY.`
                  : 'Your available workspaces will appear here when account access is assigned.'}
              </p>
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-800 bg-slate-900/55 p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-amber-400/20 bg-amber-400/10 text-amber-200">
              <Sparkles className="h-4 w-4" />
            </span>
            <div>
              <h2 className="font-semibold text-white">Need another workspace?</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                Workspace access is managed by your assigned permissions. Contact your platform administrator to request a change.
              </p>
            </div>
          </div>
        </article>
      </section>
    </div>
  )
}