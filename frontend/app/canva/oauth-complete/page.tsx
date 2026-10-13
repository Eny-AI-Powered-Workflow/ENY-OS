// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/canva/oauth-complete/page.tsx
'use client'

import { useEffect } from 'react'
import { useState } from 'react'

export default function CanvaOAuthCompletePage() {
  const [message, setMessage] = useState('Finishing Canva authorization…')

  useEffect(() => {
    const status = new URLSearchParams(window.location.search).get('canva')
    const result = {
      type: 'eny-canva-oauth-complete',
      status: status === 'connected' ? 'connected' : 'error',
    }

    if (typeof BroadcastChannel !== 'undefined') {
      const channel = new BroadcastChannel('eny-canva-oauth')
      channel.postMessage(result)
      channel.close()
    }

    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(result, window.location.origin)
    }
    window.close()

    const closeCheck = window.setTimeout(() => {
      if (!window.closed) {
        setMessage(status === 'connected'
          ? 'Canva authorization is complete. This window should close automatically; you can close it if it remains open.'
          : 'Canva authorization did not complete. Return to the Videographer dashboard and try again.')
      }
    }, 500)
    return () => window.clearTimeout(closeCheck)
  }, [])

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#050816] px-6 text-center text-white">
      <p role="status">{message}</p>
    </main>
  )
}
