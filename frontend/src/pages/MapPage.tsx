import { useQuery } from '@tanstack/react-query'
import { fetchObservations, fetchChokePoints } from '@/api/endpoints'
import { ArgusMap } from '@/components/map/ArgusMap'
import { LayerManager } from '@/components/map/LayerManager'
import { useAOIStore } from '@/store/aoiStore'
import { useMapStore } from '@/store/mapStore'

export function MapPage() {
  const { selectedAOI, selectedObservation, setSelectedObservation } = useAOIStore()
  const { activeLayers } = useMapStore()
  const aoiId = selectedAOI?.id ?? ''

  const { data: obsData } = useQuery({
    queryKey: ['obs', aoiId],
    queryFn: () => fetchObservations(aoiId),
    enabled: !!aoiId,
  })

  const { data: chokeData } = useQuery({
    queryKey: ['choke', aoiId],
    queryFn: () => fetchChokePoints(aoiId),
    enabled: !!aoiId,
  })

  return (
    <div className="relative h-full w-full page-enter">
      <ArgusMap
        aoi={selectedAOI ?? undefined}
        observations={obsData?.items ?? []}
        chokePoints={chokeData?.items ?? []}
        activeLayers={activeLayers}
        onObservationClick={setSelectedObservation}
        className="h-full w-full"
      />
      <LayerManager />

      {/* Observation detail drawer */}
      {selectedObservation && (
        <div className="absolute right-4 top-4 w-72 rounded-xl border border-slate-800 bg-slate-900/95 backdrop-blur p-4 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <p className="font-semibold text-slate-200 capitalize">{selectedObservation.obs_type.replace(/_/g, ' ')}</p>
            <button
              onClick={() => setSelectedObservation(null)}
              className="text-slate-500 hover:text-slate-300"
            >
              ✕
            </button>
          </div>
          <div className="grid grid-cols-2 gap-y-1 text-slate-400">
            <span>Confidence</span><span className="text-slate-200">{Math.round(selectedObservation.confidence * 100)}%</span>
            <span>Evidence</span><span className="text-slate-200 capitalize">{selectedObservation.evidence_class}</span>
            <span>Status</span><span className="text-slate-200 capitalize">{selectedObservation.status}</span>
            {selectedObservation.value != null && (
              <><span>Value</span><span className="text-slate-200">{selectedObservation.value} {selectedObservation.unit ?? ''}</span></>
            )}
            {selectedObservation.area_km2 > 0 && (
              <><span>Area</span><span className="text-slate-200">{selectedObservation.area_km2.toFixed(2)} km²</span></>
            )}
          </div>
          <p className="text-[10px] text-slate-600 font-mono truncate">{selectedObservation.id}</p>
        </div>
      )}
    </div>
  )
}
