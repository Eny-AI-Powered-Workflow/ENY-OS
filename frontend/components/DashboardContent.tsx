// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/components/DashboardContent.tsx
import { Widget } from './Widget'

export function DashboardContent() {
  return (
    <div className="space-y-6">
      <h2 className="sr-only">Dashboard Overview</h2>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Widget
          title="Active Students"
          value="124"
          change="+12% from last month"
          icon="Users"
          trend="up"
        />
        <Widget
          title="New Leads"
          value="89"
          change="+5% from last week"
          icon="Mail"
          trend="up"
        />
        <Widget
          title="Revenue"
          value="$45,200"
          change="+8% quarterly"
          icon="DollarSign"
          trend="up"
        />
        <Widget
          title="Course Completion"
          value="78%"
          change="+3% from last month"
          icon="CheckCircle"
          trend="up"
        />
      </div>
    </div>
  )
}