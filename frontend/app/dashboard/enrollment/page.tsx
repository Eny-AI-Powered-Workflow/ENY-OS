import EnrollmentMetrics from "@/components/EnrollmentMetrics";
import EnrollmentLeads from "@/components/EnrollmentLeads";
import EnrollmentPipeline from "@/components/EnrollmentPipeline";

export default function EnrollmentDashboard() {
  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <header className="border-b border-slate-200 pb-6">
        <p className="text-[10px] uppercase tracking-[0.24em] text-violet-600">Sales workspace</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">All Leads</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
          A broad view of the live CRM inventory and enrollment pipeline. Use the Sales sub-tabs for focused queue work.
        </p>
      </header>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <EnrollmentMetrics />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EnrollmentLeads />
        <EnrollmentPipeline />
      </div>
    </div>
  );
}