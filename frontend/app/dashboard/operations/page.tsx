import OperationsMetrics from "@/components/OperationsMetrics";
import SystemStatus from "@/components/SystemStatus";
import RecentTasks from "@/components/RecentTasks";

export default function OperationsDashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col items-center text-center py-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Operations
        </h1>
        <p className="text-xl text-muted-foreground max-w-xl">
          Manage operations, track system performance, and optimize workflows
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <OperationsMetrics />
      </div>

      {/* System Status and Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SystemStatus />
        <RecentTasks />
      </div>
    </div>
  );
}