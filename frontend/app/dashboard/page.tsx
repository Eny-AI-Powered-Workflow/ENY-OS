// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/page.tsx
import { Sidebar } from '@/components/Sidebar'
import { DashboardContent } from '@/components/DashboardContent'

export default function DashboardPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-background border-b">
          <div className="px-4 py-3 sm:px-6">
            <div className="flex items-center justify-between">
              <h1 className="text-lg font-semibold text-foreground">Dashboard</h1>
              <div className="hidden md:flex items-center space-x-4">
                {/* User menu will go here */}
              </div>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <DashboardContent />
        </main>
      </div>
    </div>
  )
}