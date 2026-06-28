import { useQuery } from '@tanstack/react-query'
import { fetchStatus, fetchObservations, fetchAOIs, fetchChokePoints, fetchFloodRisk } from '@/api/endpoints'
import { MetricCard } from '@/components/ui/metric-card'
import { Card, CardContent, CardHeader, CardTitle, CardSeparator } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RiskLevelBadge } from '@/components/domain/RiskLevelBadge'
import { DomainStatusGrid } from '@/components/domain/DomainStatusGrid'
import { QuotaGauge } from '@/components/charts/QuotaGauge'
import { AIReportPanel } from '@/components/ai/AIReportPanel'
import { useAOIStore } from '@/store/aoiStore'
import { useEffect } from 'react'
import { timeAgo } from '@/lib/utils'
import { Droplets, CloudRain, Triangle, Activity, AlertTriangle, ChevronRight } from 'lucide-react'
import { ArgusMap } from '@/components/map/ArgusMap'
import { LayerManager } from '@/components/map/LayerManager'
import { useMapStore } from '@/store/mapStore'
import { SkeletonMetricRow } from '@/components/ui/skeleton'
import type { RiskLevel } from '@/api/types'
import { cn } from '@/lib/utils'

export function Overview() {
  const { selectedAOI, setSelectedAOI } = useAOIStore()
  const { activeLayers } = useMapStore()

  const { data: aoiData } = useQuery({
    queryKey: ['aois'],
    queryFn: fetchAOIs,
    staleTime: 60_000,
  })
  useEffect(() => {
    if (!selectedAOI && aoiData?.items?.length) {
      const aoi = aoiData.items.find((a) => a.active) ?? aoiData.items[0]
      setSelectedAOI(aoi)
    }
  }, [aoiData, selectedAOI, setSelectedAOI])

  const aoiId = selectedAOI?.id ?? ''

  const { data: statusData } = useQuery({
    queryKey: ['status'],
    queryFn: fetchStatus,
    refetchInterval: 60_000,
  })

  const { data: obsData, isLoading: obsLoading } = useQuery({
    queryKey: ['obs', aoiId, 'confirmed'],
    queryFn: () => fetchObservations(aoiId, { status: 'confirmed' }),
    enabled: !!aoiId,
  })

  const { data: chokeData } = useQuery({
    queryKey: ['choke', aoiId],
    queryFn: () => fetchChokePoints(aoiId),
    enabled: !!aoiId,
  })

  const { data: floodData } = useQuery({
    queryKey: ['flood', aoiId],
    queryFn: () => fetchFloodRisk(aoiId),
    enabled: !!aoiId,
  })

  const oilCount   = obsData?.items?.filter((o) => o.obs_type === 'oil_slick').length ?? 0
  const wqCount    = obsData?.items?.filter((o) => ['chlorophyll_a','turbidity','cdom','surface_temp'].includes(o.obs_type)).length ?? 0
  const chokeCount = chokeData?.items?.length ?? 0
  const floodLevel = (floodData?.items?.[0]?.risk_level ?? null) as RiskLevel | null
  const floodScore = floodData?.items?.[0]?.risk_score ?? null

  const allObs = obsData?.items ?? []
  const firstWaterBodyId = obsData?.items?.find((o) => o.target_id)?.target_id ?? null

  const recentEvents = [
    floodLevel && floodLevel !== 'low'
      ? { id: 'f1', type: 'Flood Risk Elevated', level: floodLevel, time: '2h ago' }
      : null,
    oilCount > 0
      ? { id: 'o1', type: `Oil Slick Detected (${oilCount})`, level: 'medium' as RiskLevel, time: '4h ago' }
      : null,
    wqCount > 0
      ? { id: 'w1', type: 'High Chlorophyll Alert', level: 'high' as RiskLevel, time: '6h ago' }
      : null,
  ].filter(Boolean) as { id: string; type: string; level: RiskLevel; time: string }[]

  const riskBorderClass: Record<RiskLevel, string> = {
    extreme: 'risk-border-extreme',
    high:    'risk-border-high',
    medium:  'risk-border-medium',
    low:     'risk-border-low',
  }

  return (
    <div className="flex flex-col h-full overflow-hidden page-enter">
      {/* ── KPI Bar ─────────────────────────────────────────────── */}
      <div className="shrink-0 grid grid-cols-4 gap-3 px-4 pt-4 pb-3">
        {obsLoading ? <SkeletonMetricRow /> : (
          <>
            <MetricCard
              title="Oil Slick Detections"
              value={oilCount}
              icon={Droplets}
              iconColor="#f97316"
              trend={{ value: 'vs. 7d avg', direction: oilCount > 2 ? 'up' : 'flat', positive: false }}
            />
            <MetricCard
              title="WQ Alerts"
              value={wqCount}
              icon={Activity}
              iconColor="#3b82f6"
              trend={{ value: 'Active observations', direction: 'flat' }}
            />
            <MetricCard
              title="Flood Risk"
              value={floodLevel ? floodLevel.toUpperCase() : 'CLEAR'}
              icon={CloudRain}
              iconColor={floodLevel === 'extreme' ? '#ef4444' : floodLevel === 'high' ? '#f97316' : '#38bdf8'}
              subtitle={floodScore != null ? `Score: ${floodScore.toFixed(3)}` : undefined}
            />
            <MetricCard
              title="Choke Points"
              value={chokeCount}
              icon={Triangle}
              iconColor="#a78bfa"
              subtitle="Flow constrictions"
            />
          </>
        )}
      </div>

      {/* ── Map + Right Panel ────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 gap-3 px-4 pb-4">
        {/* Map */}
        <div className="relative flex-1 min-w-0 rounded-xl overflow-hidden border border-[#1e293b]">
          <ArgusMap
            aoi={selectedAOI ?? undefined}
            observations={allObs}
            chokePoints={chokeData?.items ?? []}
            activeLayers={activeLayers}
            className="h-full w-full"
          />
          <LayerManager />

          {/* Map footer HUD */}
          <div className="map-hud bottom-3 left-3 right-3 flex items-center justify-between">
            <div className="glass rounded-lg px-2.5 py-1.5 flex items-center gap-3">
              {statusData && (
                <>
                  <span className="flex items-center gap-1.5 text-[11px] text-slate-500">
                    <span className={cn(
                      'h-1.5 w-1.5 rounded-full',
                      statusData.store_accessible ? 'bg-green-400' : 'bg-red-400'
                    )} />
                    {statusData.store_accessible ? 'Online' : 'Offline'}
                  </span>
                  {statusData.last_analysis_run_at && (
                    <span className="text-[11px] text-slate-600">
                      Last run {timeAgo(statusData.last_analysis_run_at)}
                    </span>
                  )}
                </>
              )}
            </div>
            <div className="map-coord-display">
              {selectedAOI?.name ?? 'No AOI selected'}
            </div>
          </div>
        </div>

        {/* Right panel */}
        <div className="w-[340px] shrink-0 flex flex-col gap-3 overflow-y-auto">
          {/* Recent Events */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Live Events</CardTitle>
                <button
                  className="flex items-center gap-0.5 text-[11px] text-blue-400 hover:text-blue-300 transition-colors"
                  aria-label="View all alerts"
                >
                  All alerts <ChevronRight className="h-3 w-3" />
                </button>
              </div>
            </CardHeader>
            <CardContent className="pt-1 space-y-0">
              {recentEvents.length === 0 ? (
                <p className="text-xs text-slate-600 py-3 text-center">No active events.</p>
              ) : (
                recentEvents.map((event) => (
                  <div
                    key={event.id}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2.5 -mx-4 first:border-t border-b border-slate-800/60',
                      'hover:bg-[#141d2e] transition-colors cursor-pointer',
                      riskBorderClass[event.level],
                    )}
                  >
                    <AlertTriangle
                      className="h-3.5 w-3.5 shrink-0"
                      style={{
                        color: event.level === 'extreme' || event.level === 'high'
                          ? '#ef4444' : event.level === 'medium' ? '#f59e0b' : '#22c55e'
                      }}
                      aria-hidden="true"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-slate-200 leading-tight">{event.type}</p>
                      <p className="text-[10px] text-slate-600 mt-0.5">{event.time}</p>
                    </div>
                    <RiskLevelBadge level={event.level} />
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* AI Brief */}
          {firstWaterBodyId ? (
            <AIReportPanel targetId={firstWaterBodyId} />
          ) : (
            <Card>
              <div className="px-4 py-5 text-center">
                <p className="text-xs text-slate-600">
                  Run the inland_wq domain to enable AI situation reports.
                </p>
              </div>
            </Card>
          )}

          {/* System Health — compact */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>System Health</CardTitle>
                {statusData && (
                  <Badge variant={statusData.store_accessible ? 'success' : 'danger'}>
                    {statusData.store_accessible ? 'Healthy' : 'Degraded'}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <DomainStatusGrid />
              {statusData && (
                <div className="mt-3 space-y-2.5">
                  <QuotaGauge
                    used={statusData.quota.cdse_bytes_today}
                    limit={statusData.quota.cdse_daily_limit_gb * 1e9}
                    label="CDSE Bandwidth"
                    unit="bytes"
                  />
                  <QuotaGauge
                    used={statusData.open_meteo_calls_today}
                    limit={10_000}
                    label="Open-Meteo API"
                    unit="calls"
                  />
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
