"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import CEOHeatmap from "@/components/CEOHeatmap";
import CEOMetrics from "@/components/CEOMetrics";
import CEOAgentStatus from "@/components/CEOAgentStatus";
import SOPLibrary from "@/components/SOPLibrary";
import SalesOperationsPanel from "@/components/SalesOperationsPanel";
import ExecutiveAssistantBriefing from "@/components/ExecutiveAssistantBriefing";
import CEOSignupManagement from "@/components/CEOSignupManagement";
import { CEO_COCKPIT_SECTIONS } from "@/lib/permissions";

export default function CEODashboard() {
  const [sectionsMenuOpen, setSectionsMenuOpen] = useState(false);
  const [activeSection, setActiveSection] = useState("overview");

  useEffect(() => {
    const updateActiveSection = () => {
      const section = window.location.hash.slice(1);
      setActiveSection(CEO_COCKPIT_SECTIONS.some((item) => item.id === section) ? section : "overview");
    };

    updateActiveSection();
    window.addEventListener("hashchange", updateActiveSection);
    return () => window.removeEventListener("hashchange", updateActiveSection);
  }, []);

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
        aria-label="CEO cockpit section menu"
        className="sticky top-0 z-20 -mx-4 border-y border-slate-800/90 bg-slate-950/95 px-4 py-3 backdrop-blur-xl sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8"
      >
        <button
          type="button"
          aria-expanded={sectionsMenuOpen}
          aria-controls="ceo-cockpit-section-links"
          onClick={() => setSectionsMenuOpen((open) => !open)}
          className="flex min-h-10 w-full items-center justify-between rounded-lg border border-slate-700/80 bg-slate-900/70 px-3 text-left text-sm font-medium text-white transition hover:border-cyan-400/50 hover:bg-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-300 sm:w-auto sm:min-w-56"
        >
          <span>
            <span className="block text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
              Cockpit sections
            </span>
            <span className="mt-0.5 block">{CEO_COCKPIT_SECTIONS.find((item) => item.id === activeSection)?.label}</span>
          </span>
          {sectionsMenuOpen
            ? <ChevronUp aria-hidden="true" className="ml-4 h-4 w-4 text-cyan-200" />
            : <ChevronDown aria-hidden="true" className="ml-4 h-4 w-4 text-cyan-200" />}
        </button>

        {sectionsMenuOpen && (
          <ul id="ceo-cockpit-section-links" className="mt-2 grid gap-2 border-t border-slate-800 pt-3 sm:grid-cols-2 xl:grid-cols-3">
            {CEO_COCKPIT_SECTIONS.map((item) => (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  aria-current={activeSection === item.id ? "location" : undefined}
                  onClick={() => setSectionsMenuOpen(false)}
                  className={`inline-flex min-h-10 w-full items-center rounded-lg border px-3 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-300 ${
                    activeSection === item.id
                      ? "border-cyan-400/50 bg-cyan-400/10 text-white"
                      : "border-slate-700/80 bg-slate-900/70 text-slate-300 hover:border-cyan-400/50 hover:bg-cyan-400/10 hover:text-white"
                  }`}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        )}
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