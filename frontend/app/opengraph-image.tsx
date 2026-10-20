// /home/obed/Documents/Eny_consulting/Eny_consulting/frontend/app/opengraph-image.tsx
import { ImageResponse } from 'next/og'

export const alt = 'ENY OS — One workspace for how ENY runs.'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: 'center',
          background: '#142238',
          color: '#ffffff',
          display: 'flex',
          height: '100%',
          justifyContent: 'space-between',
          padding: '80px',
          width: '100%',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', maxWidth: 780 }}>
          <div style={{ color: '#f0ca79', fontSize: 24, letterSpacing: 3 }}>INTERNAL PLATFORM · ENY CONSULTING INC.</div>
          <div style={{ fontSize: 76, fontWeight: 700, letterSpacing: -3, lineHeight: 1.08, marginTop: 28 }}>One workspace for how ENY runs.</div>
          <div style={{ color: '#cbd5e1', fontSize: 28, marginTop: 28 }}>ENY OS</div>
        </div>
        <div style={{ alignItems: 'center', background: '#e2b75e', borderRadius: 28, color: '#142238', display: 'flex', fontSize: 52, fontWeight: 800, height: 120, justifyContent: 'center', width: 120 }}>ENY</div>
      </div>
    ),
    size,
  )
}
