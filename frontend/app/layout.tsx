// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/layout.tsx
import type { Metadata } from 'next'
import AuthRedirect from './auth-redirect'

export const metadata: Metadata = {
  title: 'ENY Consulting Platform',
  description: 'Unified AI-powered platform for ENY Consulting',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <AuthRedirect />
        {children}
      </body>
    </html>
  )
}