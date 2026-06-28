import { useMapStore } from '@/store/mapStore'
import { cn } from '@/lib/utils'
import { Layers } from 'lucide-react'
import { useState } from 'react'

const LAYERS = [
  { id: 'observations' as const,  label: 'Oil Slicks',     color: '#f97316' },
  { id: 'wq' as const,            label: 'Water Quality',  color: '#3b82f6' },
  { id: 'flood_risk' as const,    label: 'Flood Risk',     color: '#38bdf8' },
  { id: 'choke_points' as const,  label: 'Choke Points',  color: '#a78bfa' },
  { id: 'trajectory' as const,    label: 'Trajectories',   color: '#38bdf8' },
  { id: 'acid_risk' as const,     label: 'Acid Risk',      color: '#f59e0b' },
]

export function LayerManager() {
  const { activeLayers, toggleLayer } = useMapStore()
  const [open, setOpen] = useState(false)

  return (
    <div className="absolute top-4 right-4 z-[1000]">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          'flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900/90 px-2.5 py-1.5',
          'text-xs text-slate-300 hover:text-slate-100 backdrop-blur transition-colors',
          open && 'border-blue-500/50 text-blue-400',
        )}
      >
        <Layers className="h-3.5 w-3.5" />
        Layers
      </button>

      {open && (
        <div className="absolute right-0 top-9 w-44 rounded-xl border border-slate-700 bg-slate-900/95 shadow-xl backdrop-blur p-2 space-y-0.5">
          <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Map Layers
          </p>
          {LAYERS.map((layer) => {
            const active = activeLayers.has(layer.id)
            return (
              <button
                key={layer.id}
                onClick={() => toggleLayer(layer.id)}
                className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-xs text-slate-300 hover:bg-slate-800 transition-colors"
              >
                <span
                  className="h-2 w-2 rounded-sm shrink-0"
                  style={{ background: active ? layer.color : '#334155' }}
                />
                <span className={active ? 'text-slate-200' : 'text-slate-500'}>{layer.label}</span>
                {active && <span className="ml-auto text-[10px] text-blue-400">✓</span>}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
