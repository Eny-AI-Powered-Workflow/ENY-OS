import CEOHeatmap from "@/components/CEOHeatmap";
import CEOMetrics from "@/components/CEOMetrics";
import CEOAgentStatus from "@/components/CEOAgentStatus";
import SOPLibrary from "@/components/SOPLibrary";
import SalesOperationsPanel from "@/components/SalesOperationsPanel";
import ExecutiveAssistantBriefing from "@/components/ExecutiveAssistantBriefing";
import CEOSignupManagement from "@/components/CEOSignupManagement";

export default function CEODashboard() {
  return (
    <div className="space-y-8 pb-8 lg:space-y-10">
      <header className="flex flex-col gap-4 border-b border-slate-800/80 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200">
            Executive workspace
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            CEO cockpit
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base">
            A focused view of business performance, sales operations, and the work that needs your attention.
          </p>
        </div>
      </header>

      <section aria-labelledby="ceo-metrics-heading" className="space-y-4">
        <div>
          <h2 id="ceo-metrics-heading" className="text-lg font-semibold text-white">
            Performance at a glance
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Current platform activity and system health.
          </p>
        </div>
        <CEOMetrics />
      </section>

      <section aria-labelledby="sales-operations-heading" className="space-y-4">
        <div>
          <h2 id="sales-operations-heading" className="text-lg font-semibold text-white">
            Sales and enrollment operations
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Pipeline health, follow-up, and operational exceptions.
          </p>
        </div>
        <SalesOperationsPanel />
      </section>

      <section aria-label="Executive assistant briefing">
        <ExecutiveAssistantBriefing headingLevel="h2" />
      </section>

      <section aria-labelledby="platform-activity-heading" className="space-y-4">
        <div>
          <h2 id="platform-activity-heading" className="text-lg font-semibold text-white">
            Platform activity
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Recent team activity and the current state of automations.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <CEOHeatmap />
          <CEOAgentStatus />
        </div>
      </section>

      <section aria-label="Account access management">
        <CEOSignupManagement />
      </section>

      <section aria-label="SOP knowledge library">
        <SOPLibrary />
      </section>
    </div>
  );
}