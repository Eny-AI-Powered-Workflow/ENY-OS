// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/dashboard/layout.tsx
import { Sidebar } from './Sidebar'
import { DashboardContent } from './DashboardContent'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-background border-b">
          {/* Header content will go here */}
          <div className="px-4 py-3 sm:px-6">
            <div className="flex items-center justify-between">
              <h1 className="text-lg font-semibold">ENY Consulting Platform</h1>
              <div className="flex items-center space-x-4">
                {/* User menu will go here */}
              </div>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}