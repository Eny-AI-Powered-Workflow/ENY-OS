import GraphicDesignerWorkspace from '@/components/GraphicDesignerWorkspace'

export default function GraphicDesignerPage() {
  return (
    <div className="space-y-6">
      <header>
        <p className="text-[10px] uppercase tracking-[0.2em] text-teal-300">Design operations</p>
        <h1 className="mt-1 text-3xl font-semibold text-white">Graphic & Funnel Designer</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-300">Manage ENY’s versioned brand foundation and audience-specific visual guidance.</p>
      </header>
      <GraphicDesignerWorkspace />
    </div>
  )
}
