// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/enrollment/alerts/page.tsx
import PlatformAlertInbox from '@/components/PlatformAlertInbox'

export default function SalesEnrollmentAlertsPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="space-y-1 pb-1">
        <p className="inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
          Platform
        </p>
        <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
          Sales &amp; Enrollment Alerts
        </h1>
        <p className="max-w-3xl text-sm leading-6 text-slate-400 sm:text-base">
          Read shared operational messages, review critical issues, and dismiss alerts from your own inbox.
        </p>
      </header>
      <PlatformAlertInbox />
    </div>
  )
}
