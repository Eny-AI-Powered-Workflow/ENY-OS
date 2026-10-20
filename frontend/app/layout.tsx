// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/layout.tsx
import './globals.css'
import type { Metadata } from 'next'
import AuthRedirect from './auth-redirect'

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'https://eny-os.vercel.app'),
  title: {
    default: 'ENY OS | Internal platform',
    template: '%s | ENY OS',
  },
  description: 'The internal workspace for ENY Consulting Inc.',
  robots: { index: false, follow: false },
  openGraph: {
    title: 'ENY OS | Internal platform',
    description: 'One workspace for how ENY runs.',
    siteName: 'ENY OS',
    type: 'website',
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