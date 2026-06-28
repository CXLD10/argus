import { useMapStore } from '@/store/mapStore'
import { cn } from '@/lib/utils'
import { Layers, Eye, EyeOff } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'

const LAYERS = [
  { id: 'observations' as const, label: 'Oil Slicks',    color: '#f97316', desc: 'SAR dark-spot detections' },
  { id: 'wq'          as const, label: 'Water Quality',  color: '#3b82f6', desc: 'Chlorophyll/turbidity obs' },
  { id: 'flood_risk'  as const, label: 'Flood Risk',     color: '#38bdf8', desc: 'Model output overlay' },
  { id: 'choke_points' as const,label: 'Choke Points',   color: '#a78bfa', desc: 'Flow constriction sites' },
  { id: 'trajectory'  as const, label: 'Trajectories',   color: '#22d3ee', desc: 'Oil drift forecast frames' },
  { id: 'acid_risk'   as const, label: 'Acid Risk',      color: '#f59e0b', desc: 'Deposition risk index' },
]

export function LayerManager() {
  const { activeLayers, toggleLayer } = useMapStore()
  const [open, setOpen] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && open) setOpen(false)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open])

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (open && panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const activeCount = activeLayers.size

  return (
    <div className="absolute top-3 right-3 z-[1000]" ref={panelRef}>
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={`Map layers (${activeCount} active)`}
        className={cn(
          'flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium',
          'backdrop-blur-md transition-all duration-150 shadow-[0_2px_8px_rgba(0,0,0,0.4)]',
          open
            ? 'border-blue-500/40 bg-[#141d2e]/95 text-blue-300'
            : 'border-[#1e293b] bg-[#0f1623]/95 text-slate-400 hover:text-slate-200 hover:border-slate-700',
        )}
      >
        <Layers className="h-3.5 w-3.5" />
        Layers
        {activeCount > 0 && (
          <span className="ml-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-blue-600/20 text-[10px] text-blue-400 font-medium">
            {activeCount}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Map layer toggles"
          className="absolute right-0 top-10 w-52 rounded-xl border border-[#1e293b] bg-[#0f1623]/98 shadow-[0_8px_32px_rgba(0,0,0,0.6)] backdrop-blur-xl p-2 animate-scale-in"
        >
          <div className="flex items-center justify-between px-2 py-1.5 mb-1">
            <p className="text-label text-slate-600">Map Layers</p>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close layer panel"
              className="text-slate-700 hover:text-slate-400 transition-colors text-xs"
            >
              ✕
            </button>
          </div>

          <div className="space-y-0.5">
            {LAYERS.map((layer) => {
              const active = activeLayers.has(layer.id)
              return (
                <button
                  key={layer.id}
                  onClick={() => toggleLayer(layer.id)}
                  aria-pressed={active}
                  aria-label={`${active ? 'Hide' : 'Show'} ${layer.label}`}
                  className={cn(
                    'flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-xs transition-all duration-100',
                    active
                      ? 'bg-[#141d2e] text-slate-200'
                      : 'text-slate-500 hover:bg-[#141d2e]/50 hover:text-slate-400',
                  )}
                >
                  <div
                    className="h-2.5 w-2.5 rounded-sm shrink-0 transition-all duration-150"
                    style={{ background: active ? layer.color : '#1e293b' }}
                  />
                  <div className="flex-1 text-left min-w-0">
                    <p className="font-medium leading-none">{layer.label}</p>
                    <p className="text-[10px] text-slate-700 mt-0.5 leading-none">{layer.desc}</p>
                  </div>
                  {active
                    ? <Eye className="h-3 w-3 text-slate-600 shrink-0" aria-hidden="true" />
                    : <EyeOff className="h-3 w-3 text-slate-800 shrink-0" aria-hidden="true" />
                  }
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
