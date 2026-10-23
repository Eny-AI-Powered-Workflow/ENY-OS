import EnrollmentMetrics from "@/components/EnrollmentMetrics";
import EnrollmentLeads from "@/components/EnrollmentLeads";
import EnrollmentPipeline from "@/components/EnrollmentPipeline";

export default function EnrollmentDashboard() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-6">
      <header className="relative overflow-hidden rounded-2xl border border-slate-700/80 bg-gradient-to-br from-slate-900 via-slate-900 to-violet-950/70 px-5 py-5 shadow-[0_18px_45px_rgba(2,6,23,0.25)] sm:px-7 sm:py-6">
        <div className="pointer-events-none absolute -right-12 -top-24 h-56 w-56 rounded-full bg-violet-500/10 blur-3xl" />
        <div className="relative">
          <p className="inline-flex items-center gap-2 rounded-full border border-violet-300/15 bg-violet-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-200">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.7)]" />
            Sales workspace
          </p>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl">Enrollment team dashboard</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
          A broad view of the live CRM inventory and enrollment pipeline. Use the Sales sub-tabs for focused queue work.
          </p>
        </div>
      </header>

      <EnrollmentMetrics />

      <div className="grid grid-cols-1 items-stretch gap-5 lg:grid-cols-2">
        <EnrollmentLeads />
        <EnrollmentPipeline />
      </div>
    </div>
  );
}