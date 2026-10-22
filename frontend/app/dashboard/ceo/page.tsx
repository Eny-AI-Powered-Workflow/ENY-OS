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

      <nav
        aria-label="CEO cockpit sections"
        className="sticky top-0 z-20 -mx-4 border-y border-slate-800/90 bg-slate-950/95 px-4 py-2 backdrop-blur-xl sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8"
      >
        <ul className="flex gap-2 overflow-x-auto py-1">
          {[
            { href: "#overview", label: "Overview" },
            { href: "#sales", label: "Sales operations" },
            { href: "#briefing", label: "Daily briefing" },
            { href: "#activity", label: "Platform activity" },
            { href: "#access", label: "Access management" },
            { href: "#knowledge", label: "SOP library" },
          ].map((item) => (
            <li key={item.href} className="shrink-0">
              <a
                href={item.href}
                className="inline-flex min-h-10 items-center rounded-lg border border-slate-700/80 bg-slate-900/70 px-3 text-sm font-medium text-slate-300 transition hover:border-cyan-400/50 hover:bg-cyan-400/10 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-300"
              >
                {item.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <section id="overview" aria-labelledby="ceo-metrics-heading" className="scroll-mt-24 space-y-4">
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

      <section id="sales" aria-labelledby="sales-operations-heading" className="scroll-mt-24 space-y-4">
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

      <section id="briefing" aria-label="Executive assistant briefing" className="scroll-mt-24">
        <ExecutiveAssistantBriefing headingLevel="h2" />
      </section>

      <section id="activity" aria-labelledby="platform-activity-heading" className="scroll-mt-24 space-y-4">
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

      <section id="access" aria-label="Account access management" className="scroll-mt-24">
        <CEOSignupManagement />
      </section>

      <section id="knowledge" aria-label="SOP knowledge library" className="scroll-mt-24">
        <SOPLibrary />
      </section>
    </div>
  );
}