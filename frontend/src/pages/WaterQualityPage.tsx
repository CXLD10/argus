import { useQuery } from '@tanstack/react-query'
import { fetchWaterbodies, fetchWQObservations, fetchWQForecasts, fetchWQAnomalies, fetchWQReport } from '@/api/endpoints'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { EvidenceClassBadge } from '@/components/domain/EvidenceClassBadge'
import { WQTrendChart } from '@/components/charts/WQTrendChart'
import { AIReportPanel } from '@/components/ai/AIReportPanel'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Droplets, Activity, AlertTriangle } from 'lucide-react'
import { formatDate } from '@/lib/utils'
import { useState } from 'react'

const WQ_TYPES = ['chlorophyll_a', 'turbidity', 'cdom', 'surface_temp'] as const

export function WaterQualityPage() {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null)
  const [obsType, setObsType] = useState<string>('chlorophyll_a')

  const { data: wbData, isLoading: wbLoading } = useQuery({
    queryKey: ['waterbodies'],
    queryFn: fetchWaterbodies,
  })

  const targetId = selectedTarget ?? wbData?.target_ids?.[0] ?? ''

  const { data: obsData, isLoading: obsLoading } = useQuery({
    queryKey: ['wq-obs', targetId, obsType],
    queryFn: () => fetchWQObservations(targetId, obsType),
    enabled: !!targetId,
  })

  const { data: anomalyData } = useQuery({
    queryKey: ['wq-anomalies', targetId],
    queryFn: () => fetchWQAnomalies(targetId),
    enabled: !!targetId,
  })

  const chartObs = obsData?.items ?? []

  const anomalyCount = anomalyData?.items?.length ?? 0

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: target list */}
      <div className="w-52 flex flex-col border-r border-slate-800 bg-slate-950">
        <div className="p-3 border-b border-slate-800">
          <p className="text-xs font-semibold text-slate-400">Water Bodies</p>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {wbLoading && <Skeleton className="h-8 w-full" />}
          {(wbData?.target_ids ?? []).map((id) => (
            <button
              key={id}
              onClick={() => setSelectedTarget(id)}
              className={`w-full text-left rounded-lg px-3 py-2 text-xs transition-colors ${
                (selectedTarget ?? wbData?.target_ids?.[0]) === id
                  ? 'bg-blue-600/20 text-blue-300 font-medium'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              <span className="font-mono truncate block">{id.slice(0, 20)}…</span>
            </button>
          ))}
          {!wbLoading && wbData?.target_ids?.length === 0 && (
            <p className="text-[10px] text-slate-600 px-2 py-4">No water bodies. Run inland_wq domain first.</p>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">Water Quality Monitor</h2>
            <p className="text-xs text-slate-500">{targetId ? `Target: ${targetId.slice(0, 24)}…` : 'Select a water body'}</p>
          </div>
          <div className="flex items-center gap-2">
            {anomalyCount > 0 && (
              <Badge variant="warning" className="gap-1">
                <AlertTriangle className="h-3 w-3" />
                {anomalyCount} anomalies
              </Badge>
            )}
          </div>
        </div>

        {/* Metric type selector */}
        <div className="flex gap-1.5">
          {WQ_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setObsType(t)}
              className={`rounded-lg px-3 py-1.5 text-xs transition-colors ${
                obsType === t
                  ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30'
                  : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
              }`}
            >
              {t.replace(/_/g, ' ')}
            </button>
          ))}
        </div>

        {/* Trend chart */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-3.5 w-3.5 text-blue-400" />
                {obsType.replace(/_/g, ' ')} trend
              </CardTitle>
              {obsData && <Badge variant="muted">{obsData.count} observations</Badge>}
            </div>
          </CardHeader>
          <CardContent>
            {obsLoading && <Skeleton className="h-48 w-full" />}
            {!obsLoading && chartObs.length === 0 && (
              <EmptyState
                icon={Activity}
                title="No data"
                description="No observations recorded for this metric."
                className="py-8"
              />
            )}
            {chartObs.length > 0 && (
              <WQTrendChart
                observations={chartObs}
                obsType={obsType}
              />
            )}
          </CardContent>
        </Card>

        {/* Observations table */}
        <Card>
          <CardHeader><CardTitle>Recent Observations</CardTitle></CardHeader>
          <CardContent>
            {(obsData?.items ?? []).slice(0, 10).length === 0 ? (
              <p className="text-xs text-slate-500 py-2">No observations.</p>
            ) : (
              <div className="space-y-0">
                {(obsData?.items ?? []).slice(0, 10).map((obs) => (
                  <div key={obs.id} className="flex items-center justify-between py-2 border-b border-slate-800 last:border-0">
                    <div>
                      <p className="text-xs text-slate-200">
                        {obs.value != null ? `${obs.value} ${obs.unit ?? ''}` : '—'}
                      </p>
                      <p className="text-[10px] text-slate-500">{formatDate(obs.created_at)}</p>
                    </div>
                    <EvidenceClassBadge value={obs.evidence_class} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* AI report */}
        {targetId && <AIReportPanel targetId={targetId} />}
      </div>
    </div>
  )
}
