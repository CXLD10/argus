import { Bell, Search, Settings, RefreshCw } from 'lucide-react'
import { useAOIStore } from '@/store/aoiStore'
import { useQuery } from '@tanstack/react-query'
import { fetchAOIs } from '@/api/endpoints'
import { cn } from '@/lib/utils'

export function Header() {
  const { selectedAOI, setSelectedAOI } = useAOIStore()
  const { data: aoiData } = useQuery({
    queryKey: ['aois'],
    queryFn: fetchAOIs,
    staleTime: 60_000,
  })

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-800 bg-slate-950/90 px-4">
      {/* Search */}
      <div className="flex flex-1 items-center gap-2 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Search locations, layers, targets…"
            className={cn(
              'w-full h-8 rounded-md border border-slate-800 bg-slate-900',
              'pl-8 pr-3 text-sm text-slate-300 placeholder:text-slate-600',
              'focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30',
              'transition-colors',
            )}
          />
        </div>
      </div>

      {/* AOI Selector */}
      {aoiData && aoiData.items.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900">
          <div className="h-1.5 w-1.5 rounded-full bg-green-400 pulse-glow" />
          <select
            value={selectedAOI?.id ?? ''}
            onChange={(e) => {
              const aoi = aoiData.items.find((a) => a.id === e.target.value)
              if (aoi) setSelectedAOI(aoi)
            }}
            className="bg-transparent text-sm text-slate-200 focus:outline-none cursor-pointer"
          >
            {aoiData.items.map((aoi) => (
              <option key={aoi.id} value={aoi.id} className="bg-slate-900">
                {aoi.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Right actions */}
      <div className="flex items-center gap-1 ml-auto">
        <button className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors">
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
        <button className="relative flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors">
          <Bell className="h-3.5 w-3.5" />
          <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-red-500" />
        </button>
        <button className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors">
          <Settings className="h-3.5 w-3.5" />
        </button>
        <div className="ml-1 h-7 w-7 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white cursor-pointer">
          J
        </div>
      </div>
    </header>
  )
}
