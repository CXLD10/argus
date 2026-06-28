import { useQuery } from '@tanstack/react-query'
import { fetchObservations, fetchPredictions } from '@/api/endpoints'
import { useAOIStore } from '@/store/aoiStore'
import { useMapStore } from '@/store/mapStore'
import { ArgusMap } from '@/components/map/ArgusMap'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { EvidenceClassBadge } from '@/components/domain/EvidenceClassBadge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Droplets } from 'lucide-react'
import { formatDate, confidenceColor } from '@/lib/utils'

export function OilMonitoringPage() {
  const { selectedAOI, setSelectedObservation, selectedObservation } = useAOIStore()
  const { activeLayers } = useMapStore()
  const aoiId = selectedAOI?.id ?? ''

  const { data: obsData, isLoading } = useQuery({
    queryKey: ['obs', aoiId, 'oil_slick'],
    queryFn: () => fetchObservations(aoiId, { obs_type: 'oil_slick' }),
    enabled: !!aoiId,
  })

  const { data: predData } = useQuery({
    queryKey: ['preds', aoiId],
    queryFn: () => fetchPredictions(aoiId),
    enabled: !!aoiId,
  })

  const slicks = obsData?.items ?? []

  return (
    <div className="flex h-full">
      {/* Map panel */}
      <div className="relative flex-1 min-w-0">
        <ArgusMap
          aoi={selectedAOI ?? undefined}
          observations={slicks}
          trajectoryFrames={predData?.items?.[0]?.frames ?? []}
          activeLayers={activeLayers}
          onObservationClick={setSelectedObservation}
          className="h-full"
        />
      </div>

      {/* Side panel */}
      <div className="w-80 flex flex-col border-l border-slate-800 bg-slate-950 overflow-y-auto">
        <div className="p-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Droplets className="h-4 w-4 text-orange-400" />
            <h2 className="text-sm font-semibold text-slate-200">Oil Slick Detections</h2>
            <Badge variant="muted" className="ml-auto">{slicks.length}</Badge>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isLoading && Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}

          {!isLoading && slicks.length === 0 && (
            <EmptyState
              icon={Droplets}
              title="No slicks detected"
              description="Run the marine_oil domain to search for SAR dark-spot signatures."
              className="m-4"
            />
          )}

          {slicks.map((obs) => (
            <button
              key={obs.id}
              onClick={() => setSelectedObservation(obs)}
              className={`w-full text-left rounded-lg p-3 border transition-colors ${
                selectedObservation?.id === obs.id
                  ? 'border-blue-500/40 bg-blue-500/10'
                  : 'border-slate-800 hover:bg-slate-900'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-slate-200 truncate">
                    {obs.area_km2.toFixed(2)} km²
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">{formatDate(obs.created_at)}</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <EvidenceClassBadge value={obs.evidence_class} />
                  <span
                    className="text-[10px] font-medium"
                    style={{ color: confidenceColor(obs.confidence) }}
                  >
                    {Math.round(obs.confidence * 100)}% conf.
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Trajectory predictions */}
        {predData && predData.items.length > 0 && (
          <div className="border-t border-slate-800 p-4">
            <p className="text-xs font-semibold text-slate-400 mb-2">Trajectory Forecasts</p>
            {predData.items.map((pred) => (
              <div key={pred.id} className="flex items-center justify-between py-1">
                <p className="text-xs text-slate-300">{pred.frames.length} frames</p>
                <EvidenceClassBadge value={pred.evidence_class as 'measured' | 'modeled' | 'inferred'} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
