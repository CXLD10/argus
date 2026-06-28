import { useQuery } from '@tanstack/react-query'
import { fetchObservations, fetchFloodRisk, fetchAcidRisk } from '@/api/endpoints'
import { useAOIStore } from '@/store/aoiStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RiskLevelBadge } from '@/components/domain/RiskLevelBadge'
import { EmptyState } from '@/components/ui/empty-state'
import { SkeletonListItem } from '@/components/ui/skeleton'
import { Bell, Droplets, CloudRain, Activity, ChevronRight } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { RiskLevel } from '@/api/types'

interface AlertRow {
  id: string
  type: string
  domain: string
  domainLabel: string
  severity: RiskLevel
  message: string
  time: string
  icon: LucideIcon
}

const SEVERITY_ORDER: Record<RiskLevel, number> = { extreme: 0, high: 1, medium: 2, low: 3 }

const borderClass: Record<RiskLevel, string> = {
  extreme: 'risk-border-extreme',
  high:    'risk-border-high',
  medium:  'risk-border-medium',
  low:     'risk-border-low',
}

const iconColorMap: Record<RiskLevel, string> = {
  extreme: '#ef4444',
  high:    '#f97316',
  medium:  '#f59e0b',
  low:     '#22c55e',
}

export function AlertsPage() {
  const { selectedAOI } = useAOIStore()
  const aoiId = selectedAOI?.id ?? ''

  const { data: obsData, isLoading: obsLoading } = useQuery({
    queryKey: ['obs', aoiId, 'confirmed'],
    queryFn: () => fetchObservations(aoiId, { status: 'confirmed' }),
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

  const isLoading = obsLoading || floodLoading || acidLoading

  const alerts: AlertRow[] = []

  for (const pred of floodData?.items ?? []) {
    if (pred.risk_level && pred.risk_level !== 'low' && pred.risk_score != null) {
      alerts.push({
        id: `flood-${pred.id}`,
        type: 'Flood Risk Elevated',
        domain: 'weather_hydro',
        domainLabel: 'D3 · Weather/Hydro',
        severity: pred.risk_level,
        message: `Composite risk score ${pred.risk_score.toFixed(3)} — threshold exceeded`,
        time: pred.created_at,
        icon: CloudRain,
      })
    }
  }

  for (const pred of acidData?.items ?? []) {
    if (pred.acid_risk_index != null && pred.acid_risk_index >= 7) {
      alerts.push({
        id: `acid-${pred.id}`,
        type: 'Acid Deposition Risk',
        domain: 'weather_hydro',
        domainLabel: 'D3 · Weather/Hydro',
        severity: pred.acid_risk_index >= 9 ? 'extreme' : 'high',
        message: `Acid Risk Index ${pred.acid_risk_index.toFixed(1)}/10 — atmospheric deposition model (not pH)`,
        time: pred.created_at,
        icon: Activity,
      })
    }
  }

  for (const obs of obsData?.items?.filter((o) => o.obs_type === 'oil_slick') ?? []) {
    alerts.push({
      id: `oil-${obs.id}`,
      type: 'Oil Slick Confirmed',
      domain: 'marine_oil',
      domainLabel: 'D1 · Marine Oil',
      severity: obs.confidence >= 0.8 ? 'high' : 'medium',
      message: `${obs.area_km2.toFixed(2)} km² · Confidence ${Math.round(obs.confidence * 100)}%`,
      time: obs.created_at,
      icon: Droplets,
    })
  }

  alerts.sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || b.time.localeCompare(a.time))

  const counts = {
    extreme: alerts.filter((a) => a.severity === 'extreme').length,
    high:    alerts.filter((a) => a.severity === 'high').length,
    medium:  alerts.filter((a) => a.severity === 'medium').length,
  }

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4 page-enter">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#141d2e] border border-[#1e293b]">
          <Bell className="h-4 w-4 text-slate-400" />
        </div>
        <div>
          <h1 className="text-title text-slate-100">Alert History</h1>
          <p className="text-caption text-slate-500">{selectedAOI?.name ?? 'No AOI selected'}</p>
        </div>
        <div className="flex gap-1.5 ml-auto">
          {counts.extreme > 0 && <Badge variant="danger">{counts.extreme} extreme</Badge>}
          {counts.high    > 0 && <Badge variant="danger">{counts.high} high</Badge>}
          {counts.medium  > 0 && <Badge variant="warning">{counts.medium} medium</Badge>}
          {alerts.length === 0 && <Badge variant="success">All clear</Badge>}
        </div>
      </div>

      <Card variant="elevated">
        <CardContent className="p-0">
          {isLoading && (
            <div className="divide-y divide-slate-800/60">
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonListItem key={i} />
              ))}
            </div>
          )}

          {!isLoading && alerts.length === 0 && (
            <EmptyState
              icon={Bell}
              title="No active alerts"
              description="Alerts are triggered when flood risk is elevated, acid risk exceeds 7.0, or oil slicks are confirmed."
            />
          )}

          {!isLoading && (
            <div role="list" aria-label="Alert events">
              {alerts.map((alert) => {
                const Icon = alert.icon
                return (
                  <div
                    key={alert.id}
                    role="listitem"
                    className={cn(
                      'flex items-start gap-3 px-4 py-3.5',
                      'border-b border-slate-800/60 last:border-0',
                      'hover:bg-[#141d2e]/40 transition-colors cursor-pointer',
                      borderClass[alert.severity],
                      'pl-[calc(1rem+3px)]',
                    )}
                  >
                    <div
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg mt-0.5"
                      style={{ background: `${iconColorMap[alert.severity]}18` }}
                    >
                      <Icon
                        className="h-3.5 w-3.5"
                        style={{ color: iconColorMap[alert.severity] }}
                        aria-hidden="true"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-0.5">
                        <p className="text-sm font-semibold text-slate-200 leading-tight">{alert.type}</p>
                        <RiskLevelBadge level={alert.severity} />
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">{alert.message}</p>
                      <p className="text-[11px] text-slate-600 mt-1 flex items-center gap-2">
                        <span>{alert.domainLabel}</span>
                        <span>·</span>
                        <span>{formatDate(alert.time)}</span>
                      </p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-slate-700 shrink-0 mt-1" aria-hidden="true" />
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
