import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchPredictions, fetchFloodRisk, fetchAcidRisk } from '@/api/endpoints'
import { useAOIStore } from '@/store/aoiStore'
import { useMapStore } from '@/store/mapStore'
import { ArgusMap } from '@/components/map/ArgusMap'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { EvidenceClassBadge } from '@/components/domain/EvidenceClassBadge'
import { RiskLevelBadge } from '@/components/domain/RiskLevelBadge'
import { FloodRiskGauge, AcidRiskGauge } from '@/components/charts/RiskScoreGauge'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import { TrendingUp, ChevronLeft, ChevronRight } from 'lucide-react'
import { formatDate } from '@/lib/utils'

export function PredictionsPage() {
  const { selectedAOI } = useAOIStore()
  const { activeLayers } = useMapStore()
  const aoiId = selectedAOI?.id ?? ''
  const [frameIdx, setFrameIdx] = useState(0)

  const { data: predData, isLoading: predLoading } = useQuery({
    queryKey: ['preds', aoiId],
    queryFn: () => fetchPredictions(aoiId),
    enabled: !!aoiId,
  })

  const { data: floodData } = useQuery({
    queryKey: ['flood', aoiId],
    queryFn: () => fetchFloodRisk(aoiId),
    enabled: !!aoiId,
  })

  const { data: acidData } = useQuery({
    queryKey: ['acid', aoiId],
    queryFn: () => fetchAcidRisk(aoiId),
    enabled: !!aoiId,
  })

  const preds = predData?.items ?? []
  const activePred = preds[0] ?? null
  const frames = activePred?.frames ?? []
  const currentFrame = frames[frameIdx] ?? null

  return (
    <div className="flex h-full">
      {/* Trajectory map */}
      <div className="relative flex-1 min-w-0">
        <ArgusMap
          aoi={selectedAOI ?? undefined}
          trajectoryFrames={currentFrame ? [currentFrame] : []}
          activeLayers={new Set(['trajectory'])}
          className="h-full"
        />

        {/* Frame player */}
        {frames.length > 0 && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-3 rounded-xl border border-slate-700 bg-slate-900/95 backdrop-blur px-4 py-2">
            <button
              onClick={() => setFrameIdx((i) => Math.max(0, i - 1))}
              disabled={frameIdx === 0}
              className="disabled:opacity-30 text-slate-400 hover:text-slate-200"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <p className="text-xs text-slate-300 min-w-0 text-center">
              T+{frameIdx + 1} / {frames.length}
              {currentFrame && <span className="text-slate-500 ml-2">{formatDate(currentFrame.valid_at)}</span>}
            </p>
            <button
              onClick={() => setFrameIdx((i) => Math.min(frames.length - 1, i + 1))}
              disabled={frameIdx === frames.length - 1}
              className="disabled:opacity-30 text-slate-400 hover:text-slate-200"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {/* Side panel */}
      <div className="w-80 flex flex-col border-l border-slate-800 bg-slate-950 overflow-y-auto">
        <div className="p-4 border-b border-slate-800 flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-blue-400" />
          <h2 className="text-sm font-semibold text-slate-200">Predictions</h2>
          <Badge variant="muted" className="ml-auto">{preds.length}</Badge>
        </div>

        <div className="p-4 space-y-4">
          {/* Flood risk */}
          {(floodData?.items ?? []).map((pred) => pred.risk_score != null && (
            <Card key={pred.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Flood Risk</CardTitle>
                  <RiskLevelBadge level={pred.risk_level} />
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <FloodRiskGauge score={pred.risk_score} level={pred.risk_level} />
                <div className="flex items-center justify-between">
                  <EvidenceClassBadge value={pred.evidence_class as 'measured' | 'modeled' | 'inferred'} />
                  <span className="text-[10px] text-slate-500">{formatDate(pred.created_at)}</span>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Acid risk */}
          {(acidData?.items ?? []).map((pred) => pred.acid_risk_index != null && (
            <Card key={pred.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Acid Risk</CardTitle>
                  <span className="text-xs text-slate-400">{pred.acid_risk_index.toFixed(1)}/10</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <AcidRiskGauge index={pred.acid_risk_index} />
                <p className="text-[10px] text-slate-600 italic">NOT a pH measurement.</p>
                <EvidenceClassBadge value={pred.evidence_class as 'measured' | 'modeled' | 'inferred'} />
              </CardContent>
            </Card>
          ))}

          {/* Trajectory predictions */}
          {predLoading && <Skeleton className="h-20" />}
          {preds.map((pred) => (
            <Card key={pred.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="capitalize">{pred.kind.replace(/_/g, ' ')}</CardTitle>
                  <EvidenceClassBadge value={pred.evidence_class as 'measured' | 'modeled' | 'inferred'} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-1 text-xs">
                  <span className="text-slate-500">Predictor</span>
                  <span className="text-slate-200 font-mono text-[10px]">{pred.predictor_id}</span>
                  <span className="text-slate-500">Frames</span>
                  <span className="text-slate-200">{pred.frames.length}</span>
                  <span className="text-slate-500">Created</span>
                  <span className="text-slate-200">{formatDate(pred.created_at)}</span>
                </div>
              </CardContent>
            </Card>
          ))}

          {!predLoading && preds.length === 0 && !floodData?.items?.length && (
            <EmptyState
              icon={TrendingUp}
              title="No predictions"
              description="Run a predictor (oil trajectory, flood risk, acid risk) to see forecasts here."
            />
          )}
        </div>
      </div>
    </div>
  )
}
