// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/layout.tsx
import './globals.css'
import type { Metadata } from 'next'
import AuthRedirect from './auth-redirect'

export const metadata: Metadata = {
  title: 'ENY Consulting Platform',
  description: 'Unified AI-powered platform for ENY Consulting',
  metadataBase: new URL('https://enyconsulting.com'),
  icons: {
    icon: '/favicon.ico',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="antialiased bg-background text-foreground">
        {/* Google Fonts - IBM Plex */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        <AuthRedirect />
        {children}
      </body>
    </html>
  )
}