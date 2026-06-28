import { useQuery } from '@tanstack/react-query'
import { fetchChokePoints, fetchFloodRisk } from '@/api/endpoints'
import { useAOIStore } from '@/store/aoiStore'
import { useMapStore } from '@/store/mapStore'
import { ArgusMap } from '@/components/map/ArgusMap'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RiskLevelBadge } from '@/components/domain/RiskLevelBadge'
import { FloodRiskGauge } from '@/components/charts/RiskScoreGauge'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import { Triangle } from 'lucide-react'

export function ChokePointsPage() {
  const { selectedAOI } = useAOIStore()
  const { activeLayers } = useMapStore()
  const aoiId = selectedAOI?.id ?? ''

  const { data: chokeData, isLoading } = useQuery({
    queryKey: ['choke', aoiId],
    queryFn: () => fetchChokePoints(aoiId),
    enabled: !!aoiId,
  })

  const { data: floodData } = useQuery({
    queryKey: ['flood', aoiId],
    queryFn: () => fetchFloodRisk(aoiId),
    enabled: !!aoiId,
  })

  const chokes = chokeData?.items ?? []
  const latestFlood = floodData?.items?.[0] ?? null

  return (
    <div className="flex h-full page-enter">
      {/* Map */}
      <div className="relative flex-1 min-w-0">
        <ArgusMap
          aoi={selectedAOI ?? undefined}
          chokePoints={chokes}
          activeLayers={new Set(['choke_points'])}
          className="h-full"
        />
      </div>

      {/* Side panel */}
      <div className="w-80 flex flex-col border-l border-slate-800 bg-slate-950 overflow-y-auto">
        <div className="p-4 border-b border-slate-800 flex items-center gap-2">
          <Triangle className="h-4 w-4 text-violet-400" />
          <h2 className="text-sm font-semibold text-slate-200">Choke Points</h2>
          <Badge variant="muted" className="ml-auto">{chokes.length}</Badge>
        </div>

        <div className="p-4 space-y-4">
          {latestFlood && latestFlood.risk_score != null && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Flood Risk</CardTitle>
                  <RiskLevelBadge level={latestFlood.risk_level} />
                </div>
              </CardHeader>
              <CardContent>
                <FloodRiskGauge score={latestFlood.risk_score} level={latestFlood.risk_level} />
              </CardContent>
            </Card>
          )}

          {isLoading && Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}

          {!isLoading && chokes.length === 0 && (
            <EmptyState
              icon={Triangle}
              title="No choke points"
              description="Run the hydro_chokepoints domain to identify flow constrictions."
            />
          )}

          {chokes
            .slice()
            .sort((a, b) => b.constriction_score - a.constriction_score)
            .map((cp) => (
              <div key={cp.id} className="rounded-lg border border-slate-800 p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-mono text-slate-300 truncate">{cp.id.slice(0, 16)}…</p>
                  <span className="text-xs font-bold text-violet-300">
                    {(cp.constriction_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-1 w-full rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-violet-500"
                    style={{ width: `${cp.constriction_score * 100}%` }}
                  />
                </div>
                <div className="grid grid-cols-2 gap-1 text-[10px] text-slate-500">
                  <span>Upstream area</span>
                  <span className="text-slate-300">{cp.upstream_area_km2.toFixed(1)} km²</span>
                  <span>DEM source</span>
                  <span className="text-slate-300">{cp.dem_source}</span>
                  <span>Evidence</span>
                  <span className="text-slate-300 capitalize">{cp.evidence_class}</span>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
