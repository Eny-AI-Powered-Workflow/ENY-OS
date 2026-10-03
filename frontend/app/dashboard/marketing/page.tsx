import MarketingMetrics from "@/components/MarketingMetrics";
import MarketingAnalytics from "@/components/MarketingAnalytics";
import MarketingContentWorkspace from "@/components/MarketingContentWorkspace";
import MarketingIntelligence from "@/components/MarketingIntelligence";
import MarketingVideoWorkspace from "@/components/MarketingVideoWorkspace";
import MarketingOperationsReport from "@/components/MarketingOperationsReport";

export default function MarketingDashboard() {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-background p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent mb-2">
          Marketing Dashboard
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Manage campaigns, track performance, and drive growth with intelligent insights
        </p>
      </div>

      {/* Stats Overview */}
      <div className="mb-8">
        <MarketingMetrics />
      </div>

      {/* Main Content */}
      <div className="space-y-8">
        {/* Left Column */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Content Workspace */}
          <div className="col-span-1 lg:col-span-1">
            <MarketingContentWorkspace />
          </div>
          {/* Video Workspace */}
          <div className="col-span-1 lg:col-span-1">
            <MarketingVideoWorkspace />
          </div>
          {/* Intelligence */}
          <div className="col-span-1 lg:col-span-1">
            <MarketingIntelligence />
          </div>
        </div>

        {/* Full Width Sections */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MarketingAnalytics />
          <MarketingOperationsReport />
        </div>
      </div>
    </div>
  );
}