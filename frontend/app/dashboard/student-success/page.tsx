import StudentSuccessMetrics from "@/components/StudentSuccessMetrics";
import StudentList from "@/components/StudentList";
import StudentProgress from "@/components/StudentProgress";
import StudentPayments from "@/components/StudentPayments";

export default function StudentSuccessDashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col items-center text-center py-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Student Success
        </h1>
        <p className="text-xl text-muted-foreground max-w-xl">
          Student lifecycle sources and provider-reported payment records
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StudentSuccessMetrics />
      </div>

      <StudentPayments />

      {/* Students and Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StudentList />
        <StudentProgress />
      </div>
    </div>
  );
}