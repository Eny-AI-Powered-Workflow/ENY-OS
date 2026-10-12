// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/canva/oauth-complete/page.tsx
'use client'

import { useEffect } from 'react'

export default function CanvaOAuthCompletePage() {
  useEffect(() => {
    const status = new URLSearchParams(window.location.search).get('canva')
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(
        {
          type: 'eny-canva-oauth-complete',
          status: status === 'connected' ? 'connected' : 'error',
        },
        window.location.origin,
      )
      window.close()
      return
    }

    window.location.replace('/dashboard/videographer')
  }, [])

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#050816] px-6 text-center text-white">
      <p role="status">Canva authorization complete. You can close this window.</p>
    </main>
  )
}
