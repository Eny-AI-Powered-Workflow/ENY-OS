import WriterMetrics from "@/components/WriterMetrics";
import DocumentList from "@/components/DocumentList";
import AgentTemplates from "@/components/AgentTemplates";

export default function WriterDashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col items-center text-center py-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Writer & SOPs
        </h1>
        <p className="text-xl text-muted-foreground max-w-xl">
          Create, manage, and deploy documents and agent templates
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <WriterMetrics />
      </div>

      {/* Documents and Templates */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DocumentList />
        <AgentTemplates />
      </div>
    </div>
  );
}