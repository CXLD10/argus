import { useQuery } from '@tanstack/react-query'
import { fetchObservations, fetchFloodRisk, fetchAcidRisk } from '@/api/endpoints'
import { useAOIStore } from '@/store/aoiStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EvidenceClassBadge } from '@/components/domain/EvidenceClassBadge'
import { RiskLevelBadge } from '@/components/domain/RiskLevelBadge'
import { FloodRiskGauge, AcidRiskGauge } from '@/components/charts/RiskScoreGauge'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import { CloudRain, Activity } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const HYDRO_TYPES = ['precipitation', 'river_discharge', 'soil_moisture']

export function HydroPage() {
  const { selectedAOI } = useAOIStore()
  const aoiId = selectedAOI?.id ?? ''

  const { data: obsData, isLoading } = useQuery({
    queryKey: ['obs', aoiId],
    queryFn: () => fetchObservations(aoiId),
    enabled: !!aoiId,
  })

  const { data: floodData, isLoading: floodLoading } = useQuery({
    queryKey: ['flood', aoiId],
    queryFn: () => fetchFloodRisk(aoiId),
    enabled: !!aoiId,
  })

  const { data: acidData, isLoading: acidLoading } = useQuery({
    queryKey: ['acid', aoiId],
    queryFn: () => fetchAcidRisk(aoiId),
    enabled: !!aoiId,
  })

  const hydroObs = (obsData?.items ?? []).filter((o) =>
    HYDRO_TYPES.includes(o.obs_type)
  )

  const latestFlood = floodData?.items?.[0] ?? null
  const latestAcid  = acidData?.items?.[0] ?? null

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <div className="flex items-center gap-2">
        <CloudRain className="h-4 w-4 text-sky-400" />
        <h2 className="text-sm font-semibold text-slate-200">Weather &amp; Hydrology</h2>
        {selectedAOI && <span className="text-xs text-slate-500">— {selectedAOI.name}</span>}
      </div>

      {/* Risk gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Flood Risk</CardTitle>
              {latestFlood && <RiskLevelBadge level={latestFlood.risk_level} />}
            </div>
          </CardHeader>
          <CardContent>
            {floodLoading && <Skeleton className="h-12" />}
            {!floodLoading && !latestFlood && (
              <EmptyState icon={CloudRain} title="No flood prediction" description="Run weather_hydro domain to compute flood risk." />
            )}
            {latestFlood && latestFlood.risk_score != null && (
              <div className="space-y-3">
                <FloodRiskGauge score={latestFlood.risk_score} level={latestFlood.risk_level} />
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <p className="text-slate-500">Score</p>
                    <p className="text-slate-200 font-medium">{latestFlood.risk_score.toFixed(3)}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Computed</p>
                    <p className="text-slate-200 font-medium">{formatDate(latestFlood.created_at)}</p>
                  </div>
                </div>
                <EvidenceClassBadge value={latestFlood.evidence_class as 'measured' | 'modeled' | 'inferred'} />
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Acid Deposition Risk</CardTitle>
              {latestAcid?.acid_risk_index != null && (
                <span className="text-xs font-semibold text-slate-300">
                  {latestAcid.acid_risk_index.toFixed(1)}/10
                </span>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {acidLoading && <Skeleton className="h-12" />}
            {!acidLoading && !latestAcid && (
              <EmptyState icon={Activity} title="No acid risk data" description="Run weather_hydro domain to compute acid deposition risk." />
            )}
            {latestAcid && latestAcid.acid_risk_index != null && (
              <div className="space-y-3">
                <AcidRiskGauge index={latestAcid.acid_risk_index} />
                <p className="text-[10px] text-slate-600 italic">
                  Note: Acid Risk Index (0–10) is a composite atmospheric-deposition model output.
                  NOT a pH measurement.
                </p>
                <EvidenceClassBadge value={latestAcid.evidence_class as 'measured' | 'modeled' | 'inferred'} />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Hydro observations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-sky-400" />
            Hydro Observations
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <Skeleton className="h-32" />}
          {!isLoading && hydroObs.length === 0 && (
            <EmptyState icon={CloudRain} title="No hydro observations" description="Run the weather_hydro domain to ingest Open-Meteo data." />
          )}
          <div className="space-y-0">
            {hydroObs.map((obs) => (
              <div key={obs.id} className="flex items-center justify-between py-2 border-b border-slate-800 last:border-0">
                <div>
                  <p className="text-xs font-medium text-slate-200 capitalize">{obs.obs_type.replace(/_/g, ' ')}</p>
                  <p className="text-[10px] text-slate-500">
                    {obs.value != null ? `${obs.value} ${obs.unit ?? ''}` : '—'} · {formatDate(obs.created_at)}
                  </p>
                </div>
                <EvidenceClassBadge value={obs.evidence_class} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
