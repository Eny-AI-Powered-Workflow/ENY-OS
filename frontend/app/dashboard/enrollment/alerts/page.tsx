// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/enrollment/alerts/page.tsx
import PlatformAlertInbox from '@/components/PlatformAlertInbox'

export default function SalesEnrollmentAlertsPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <p className="text-[10px] uppercase tracking-[0.24em] text-violet-600">Platform</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Sales &amp; Enrollment Alerts</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
          Read shared operational messages, review critical issues, and dismiss alerts from your own inbox.
        </p>
      </header>
      <PlatformAlertInbox />
    </div>
  )
}
