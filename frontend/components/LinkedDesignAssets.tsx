'use client'

import { useEffect, useState } from 'react'
import { ExternalLink, FileImage, Loader2 } from 'lucide-react'
import { supabase } from '@/lib/supabaseClient'

type LinkedAsset = { id: string; title: string; asset_type: string; audience: string; status: string; files: Array<{ id: string; file_kind: string; original_filename: string; mime_type: string }> }

type Props = { sourceContentId?: string | null; sourceVideoAssetId?: string | null; contextLabel: string }

export default function LinkedDesignAssets({ sourceContentId, sourceVideoAssetId, contextLabel }: Props) {
  const [assets, setAssets] = useState<LinkedAsset[]>([])
  const [loading, setLoading] = useState(true)
  const [openingFile, setOpeningFile] = useState<string | null>(null)

  const headers = async (): Promise<HeadersInit> => {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}
  }

  useEffect(() => {
    let active = true
    const load = async () => {
      if (!sourceContentId && !sourceVideoAssetId) { setAssets([]); setLoading(false); return }
      setLoading(true)
      const query = new URLSearchParams()
      if (sourceContentId) query.set('source_content_id', sourceContentId)
      if (sourceVideoAssetId) query.set('source_video_asset_id', sourceVideoAssetId)
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/assets?${query}`, { headers: await headers(), credentials: 'include' })
        const payload = response.ok ? await response.json() : { assets: [] }
        if (active) setAssets((payload.assets || []).filter((asset: LinkedAsset) => ['approved', 'published'].includes(asset.status)))
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => { active = false }
  }, [sourceContentId, sourceVideoAssetId])

  const preview = async (asset: LinkedAsset, fileId: string) => {
    setOpeningFile(fileId)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/designer/assets/${asset.id}/files/${fileId}/preview`, { headers: await headers(), credentials: 'include' })
      const payload = await response.json()
      if (response.ok && payload.signed_url) window.open(payload.signed_url, '_blank', 'noopener,noreferrer')
    } finally {
      setOpeningFile(null)
    }
  }

  if (loading) return <p className="mt-2 inline-flex items-center gap-1 text-[10px] text-slate-500"><Loader2 className="h-3 w-3 animate-spin" />Loading approved design assets</p>
  if (!assets.length) return null

  return <div className="mt-3 border-t border-slate-200 pt-2"><p className="mb-2 text-[10px] font-semibold uppercase text-slate-500">Design assets linked to {contextLabel}</p><div className="flex flex-wrap gap-2">{assets.map((asset) => asset.files.map((file) => <button key={file.id} type="button" onClick={() => void preview(asset, file.id)} disabled={openingFile === file.id} className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50" title={`${asset.title} · ${file.original_filename}`}><FileImage className="h-3 w-3" />{asset.title}{openingFile === file.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <ExternalLink className="h-3 w-3" />}</button>))}</div></div>
}
