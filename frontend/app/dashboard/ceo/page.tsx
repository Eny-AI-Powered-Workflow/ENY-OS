import CEOHeatmap from "@/components/CEOHeatmap";
import CEOMetrics from "@/components/CEOMetrics";
import CEOAgentStatus from "@/components/CEOAgentStatus";

export default function CEODashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col items-center text-center py-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          CEO Cockpit
        </h1>
        <p className="text-xl text-muted-foreground max-w-xl">
          Executive overview and strategic insights
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <CEOMetrics />
      </div>

      {/* Heatmap and Agent Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CEOHeatmap />
        <CEOAgentStatus />
      </div>
    </div>
  );
}