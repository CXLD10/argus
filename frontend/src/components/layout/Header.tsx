import { Bell, Settings, RefreshCw, Search, ChevronDown } from 'lucide-react'
import { useAOIStore } from '@/store/aoiStore'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchAOIs } from '@/api/endpoints'
import { cn } from '@/lib/utils'
import { useState } from 'react'

export function Header() {
  const { selectedAOI, setSelectedAOI } = useAOIStore()
  const queryClient = useQueryClient()
  const [refreshing, setRefreshing] = useState(false)

  const { data: aoiData } = useQuery({
    queryKey: ['aois'],
    queryFn: fetchAOIs,
    staleTime: 60_000,
  })

  async function handleRefresh() {
    setRefreshing(true)
    await queryClient.invalidateQueries()
    setTimeout(() => setRefreshing(false), 800)
  }

  return (
    <header
      className="flex h-[52px] shrink-0 items-center gap-3 border-b border-[#0f1a2a] bg-[#090d1a]/95 px-4"
      role="banner"
    >
      {/* Search */}
      <div className="flex flex-1 items-center max-w-xs">
        <div className="relative w-full">
          <Search
            className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-600 pointer-events-none"
            aria-hidden="true"
          />
          <input
            type="search"
            placeholder="Search…"
            aria-label="Search observations, AOIs, and layers"
            className={cn(
              'w-full h-8 rounded-lg border border-[#1e293b] bg-[#0f1623]',
              'pl-8 pr-3 text-sm text-slate-300 placeholder:text-slate-700',
              'focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20',
              'transition-colors',
            )}
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 hidden sm:flex items-center gap-0.5 text-[10px] text-slate-700 font-mono">
            <span>⌘</span><span>K</span>
          </kbd>
        </div>
      </div>

      {/* AOI Selector */}
      {aoiData && aoiData.items.length > 0 && (
        <div className="relative flex items-center gap-2 pl-3 pr-2 py-1.5 rounded-lg border border-[#1e293b] bg-[#0f1623] hover:border-slate-700 transition-colors cursor-pointer">
          <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-green-400 shrink-0" aria-hidden="true" />
          <label htmlFor="aoi-select" className="sr-only">Area of Interest</label>
          <select
            id="aoi-select"
            value={selectedAOI?.id ?? ''}
            onChange={(e) => {
              const aoi = aoiData.items.find((a) => a.id === e.target.value)
              if (aoi) setSelectedAOI(aoi)
            }}
            className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer max-w-[160px]"
          >
            {aoiData.items.map((aoi) => (
              <option key={aoi.id} value={aoi.id} className="bg-[#141d2e]">
                {aoi.name}
              </option>
            ))}
          </select>
          <ChevronDown className="h-3 w-3 text-slate-600 pointer-events-none shrink-0" aria-hidden="true" />
        </div>
      )}

      {/* Right actions */}
      <div className="flex items-center gap-1 ml-auto">
        <button
          onClick={handleRefresh}
          aria-label="Refresh all data"
          title="Refresh all data"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-[#141d2e] hover:text-slate-300 transition-colors"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', refreshing && 'animate-spin')} />
        </button>
        <button
          aria-label="Notifications (3 unread)"
          title="Notifications"
          className="relative flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-[#141d2e] hover:text-slate-300 transition-colors"
        >
          <Bell className="h-3.5 w-3.5" />
          <span className="notif-badge" aria-label="3 unread notifications" />
        </button>
        <button
          aria-label="Settings"
          title="Settings"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-[#141d2e] hover:text-slate-300 transition-colors"
        >
          <Settings className="h-3.5 w-3.5" />
        </button>
        <div
          className="ml-1 h-7 w-7 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-[11px] font-bold text-white cursor-pointer shadow-sm"
          aria-label="User menu: Josh Admin"
          role="button"
          tabIndex={0}
        >
          J
        </div>
      </div>
    </header>
  )
}
