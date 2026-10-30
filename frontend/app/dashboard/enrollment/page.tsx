import EnrollmentMetrics from "@/components/EnrollmentMetrics";
import EnrollmentLeads from "@/components/EnrollmentLeads";
import EnrollmentPipeline from "@/components/EnrollmentPipeline";

export default function EnrollmentDashboard() {
  return (
    <div className="relative -mx-4 -my-6 min-h-full overflow-hidden bg-[#07111e] px-4 pb-10 pt-5 text-slate-100 sm:-mx-6 sm:px-6 sm:pt-6 lg:-mx-8 lg:px-8">
      <div className="pointer-events-none absolute -top-36 left-1/3 h-80 w-[42rem] rounded-full bg-cyan-400/[0.05] blur-3xl" />
      <div className="relative mx-auto w-full max-w-[1680px] space-y-4">
        <header className="relative overflow-hidden rounded-2xl border border-slate-700/60 bg-gradient-to-r from-[#101d30] via-[#15233a] to-[#17233b] px-4 py-4 shadow-[0_18px_45px_rgba(2,6,23,0.25)] sm:px-6 sm:py-5">
          <div className="pointer-events-none absolute -right-12 -top-24 h-56 w-56 rounded-full bg-cyan-400/[0.06] blur-3xl" />
          <div className="relative flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="inline-flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.7)]" />
                Sales workspace <span className="text-slate-500">/</span> Cohort conversion ops
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-semibold tracking-tight text-white sm:text-2xl">Enrollment Team Dashboard</h1>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/[0.07] px-2 py-1 text-[9px] font-medium text-emerald-300">
                  <span className="h-1 w-1 rounded-full bg-emerald-400" />Live operations
                </span>
              </div>
              <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-300 sm:text-sm">
                A broad view of the live CRM inventory and enrollment pipeline. Filter cohorts, assign leads in real time, and monitor stage conversions.
              </p>
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-white/[0.06] bg-[#0b1422]/70 px-3 py-2 text-[10px] text-slate-400">
              <span>GHL Sync Status</span>
              <span className="font-semibold text-emerald-300">Live</span>
            </div>
          </div>
        </header>

        <EnrollmentMetrics />

        <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-12">
          <div className="min-w-0 xl:col-span-7"><EnrollmentLeads /></div>
          <div className="min-w-0 xl:col-span-5"><EnrollmentPipeline /></div>
        </div>
      </div>
    </div>
  );
}
