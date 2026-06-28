import { useQuery } from '@tanstack/react-query'
import { fetchStatus, fetchObservations, fetchAOIs, fetchChokePoints, fetchFloodRisk } from '@/api/endpoints'
import { MetricCard } from '@/components/ui/metric-card'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RiskLevelBadge } from '@/components/domain/RiskLevelBadge'
import { DomainStatusGrid } from '@/components/domain/DomainStatusGrid'
import { QuotaGauge } from '@/components/charts/QuotaGauge'
import { AIReportPanel } from '@/components/ai/AIReportPanel'
import { useAOIStore } from '@/store/aoiStore'
import { useEffect } from 'react'
import { timeAgo } from '@/lib/utils'
import { Droplets, CloudRain, Triangle, Bot, AlertTriangle, Activity } from 'lucide-react'
import { ArgusMap } from '@/components/map/ArgusMap'
import { LayerManager } from '@/components/map/LayerManager'
import { useMapStore } from '@/store/mapStore'
import type { RiskLevel } from '@/api/types'

export function Overview() {
  const { selectedAOI, setSelectedAOI } = useAOIStore()
  const { activeLayers } = useMapStore()

  // Bootstrap: select first active AOI
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

  const allObs = obsData?.items ?? []

  // Simulated recent alerts (derived from obs + predictions)
  const recentAlerts = [
    floodLevel && floodLevel !== 'low'
      ? { id: 'f1', type: 'Flood Risk Increase', severity: floodLevel, time: '2h ago', aoi: selectedAOI?.name }
      : null,
    oilCount > 0
      ? { id: 'o1', type: 'Oil Slick Detected', severity: 'medium' as RiskLevel, time: '4h ago', aoi: selectedAOI?.name }
      : null,
    wqCount > 0
      ? { id: 'w1', type: 'High Chlorophyll Alert', severity: 'high' as RiskLevel, time: '6h ago', aoi: selectedAOI?.name }
      : null,
  ].filter(Boolean)

  const firstWaterBodyId = obsData?.items?.find((o) => o.target_id)?.target_id ?? null

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: map takes 60% */}
      <div className="relative flex-1 min-w-0">
        <ArgusMap
          aoi={selectedAOI ?? undefined}
          observations={allObs}
          chokePoints={chokeData?.items ?? []}
          activeLayers={activeLayers}
          className="h-full"
        />
        <LayerManager />

        {/* Bottom status overlay */}
        <div className="absolute bottom-4 left-4 right-4 flex items-center gap-2 pointer-events-none">
          {statusData && (
            <div className="glass rounded-lg px-3 py-1.5 flex items-center gap-3 text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${statusData.store_accessible ? 'bg-green-400' : 'bg-red-400'}`} />
                {statusData.store_accessible ? 'Store online' : 'Store offline'}
              </span>
              {statusData.last_analysis_run_at && (
                <span>Last run {timeAgo(statusData.last_analysis_run_at)}</span>
              )}
              <span>v{statusData.version}</span>
            </div>
          )}
        </div>
      </div>

      {/* Right panel: 380px */}
      <div className="w-96 flex flex-col border-l border-slate-800 overflow-y-auto bg-slate-950">
        <div className="p-4 space-y-4">
          {/* KPI row */}
          <div className="grid grid-cols-2 gap-2">
            <MetricCard
              title="Oil Slick Detections"
              value={oilCount}
              icon={Droplets}
              iconColor="#f97316"
              loading={obsLoading}
              trend={{ value: '+12% last 7d', positive: true }}
            />
            <MetricCard
              title="WQ Alerts"
              value={wqCount}
              icon={Activity}
              iconColor="#3b82f6"
              loading={obsLoading}
            />
            <MetricCard
              title="Flood Risk Areas"
              value={floodLevel ? '1' : '0'}
              icon={CloudRain}
              iconColor="#38bdf8"
              subtitle={floodLevel ? `Level: ${floodLevel}` : 'No active risk'}
            />
            <MetricCard
              title="Choke Points"
              value={chokeCount}
              icon={Triangle}
              iconColor="#a78bfa"
              subtitle="Monitored"
            />
          </div>

          {/* Recent Alerts */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Recent Alerts</CardTitle>
                <button className="text-[11px] text-blue-400 hover:text-blue-300">View all →</button>
              </div>
            </CardHeader>
            <CardContent>
              {recentAlerts.length === 0 ? (
                <p className="text-xs text-slate-500 py-2">No active alerts.</p>
              ) : (
                <div className="space-y-2">
                  {recentAlerts.map((alert) => alert && (
                    <div key={alert.id} className="flex items-start gap-2.5 py-1.5 border-b border-slate-800 last:border-0">
                      <AlertTriangle
                        className="h-3.5 w-3.5 mt-0.5 shrink-0"
                        style={{ color: alert.severity === 'extreme' || alert.severity === 'high' ? '#ef4444' : '#f59e0b' }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-slate-200 leading-tight">{alert.type}</p>
                        <p className="text-[10px] text-slate-500">{alert.aoi} · {alert.time}</p>
                      </div>
                      <RiskLevelBadge level={alert.severity} />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* AI Situation Summary */}
          {firstWaterBodyId ? (
            <AIReportPanel targetId={firstWaterBodyId} />
          ) : (
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><Bot className="h-3.5 w-3.5 text-blue-400" />AI Situation Summary</CardTitle></CardHeader>
              <CardContent>
                <p className="text-xs text-slate-500">Run a domain to generate the first AI report.</p>
              </CardContent>
            </Card>
          )}

          {/* System Health */}
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
                <div className="mt-3 space-y-2">
                  <QuotaGauge
                    used={statusData.quota.cdse_bytes_today}
                    limit={statusData.quota.cdse_daily_limit_gb * 1e9}
                    label="CDSE Daily Quota"
                    unit="bytes"
                  />
                  <QuotaGauge
                    used={statusData.open_meteo_calls_today}
                    limit={10_000}
                    label="Open-Meteo Calls"
                    unit="calls"
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Predictions sidebar */}
          {floodData && floodData.items.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Predictions (Next 7d)</CardTitle></CardHeader>
              <CardContent>
                {floodData.items.slice(0, 3).map((pred) => (
                  <div key={pred.id} className="flex items-center justify-between py-1.5 border-b border-slate-800 last:border-0">
                    <div>
                      <p className="text-xs font-medium text-slate-200">{pred.predictor_id}</p>
                      <p className="text-[10px] text-slate-500">{selectedAOI?.name}</p>
                    </div>
                    <RiskLevelBadge level={pred.risk_level} />
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
