import MarketingMetrics from "@/components/MarketingMetrics";
import MarketingAnalytics from "@/components/MarketingAnalytics";
import MarketingContentWorkspace from "@/components/MarketingContentWorkspace";
import MarketingIntelligence from "@/components/MarketingIntelligence";
import MarketingVideoWorkspace from "@/components/MarketingVideoWorkspace";
import MarketingOperationsReport from "@/components/MarketingOperationsReport";

export default function MarketingDashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col items-center text-center py-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Marketing
        </h1>
        <p className="text-xl text-muted-foreground max-w-xl">
          Manage campaigns, track performance, and drive growth
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MarketingMetrics />
      </div>

      <MarketingContentWorkspace />

      <MarketingIntelligence />
      <MarketingVideoWorkspace />

      <MarketingAnalytics />
      <MarketingOperationsReport />
    </div>
  );
}