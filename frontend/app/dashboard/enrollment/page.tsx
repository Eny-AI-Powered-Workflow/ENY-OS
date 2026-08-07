import EnrollmentMetrics from "@/components/EnrollmentMetrics";
import EnrollmentLeads from "@/components/EnrollmentLeads";
import EnrollmentPipeline from "@/components/EnrollmentPipeline";

export default function EnrollmentDashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col items-center text-center py-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Sales & Enrollment
        </h1>
        <p className="text-xl text-muted-foreground max-w-xl">
          Manage leads, track pipeline, and drive conversions
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <EnrollmentMetrics />
      </div>

      {/* Leads and Pipeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EnrollmentLeads />
        <EnrollmentPipeline />
      </div>
    </div>
  );
}