import { useQuery } from '@tanstack/react-query'
import { fetchObservations, fetchFloodRisk, fetchAcidRisk } from '@/api/endpoints'
import { useAOIStore } from '@/store/aoiStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RiskLevelBadge } from '@/components/domain/RiskLevelBadge'
import { EvidenceClassBadge } from '@/components/domain/EvidenceClassBadge'
import { EmptyState } from '@/components/ui/empty-state'
import { Bell, AlertTriangle, Droplets, CloudRain, Activity } from 'lucide-react'
import { formatDate } from '@/lib/utils'
import type { RiskLevel } from '@/api/types'

interface AlertRow {
  id: string
  type: string
  domain: string
  severity: RiskLevel
  message: string
  time: string
  icon: React.ComponentType<{ className?: string }>
}

export function AlertsPage() {
  const { selectedAOI } = useAOIStore()
  const aoiId = selectedAOI?.id ?? ''

  const { data: obsData } = useQuery({
    queryKey: ['obs', aoiId, 'confirmed'],
    queryFn: () => fetchObservations(aoiId, { status: 'confirmed' }),
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

  const alerts: AlertRow[] = []

  // Derive alerts from predictions
  for (const pred of floodData?.items ?? []) {
    if (pred.risk_level && pred.risk_level !== 'low' && pred.risk_score != null) {
      alerts.push({
        id: `flood-${pred.id}`,
        type: 'Flood Risk Elevated',
        domain: 'weather_hydro',
        severity: pred.risk_level,
        message: `Risk score ${pred.risk_score.toFixed(3)} — level ${pred.risk_level}`,
        time: pred.created_at,
        icon: CloudRain,
      })
    }
  }

  for (const pred of acidData?.items ?? []) {
    if (pred.acid_risk_index != null && pred.acid_risk_index >= 7) {
      alerts.push({
        id: `acid-${pred.id}`,
        type: 'Acid Deposition Risk High',
        domain: 'weather_hydro',
        severity: pred.acid_risk_index >= 9 ? 'extreme' : 'high',
        message: `Acid Risk Index ${pred.acid_risk_index.toFixed(1)}/10`,
        time: pred.created_at,
        icon: Activity,
      })
    }
  }

  // Oil slicks
  for (const obs of obsData?.items?.filter((o) => o.obs_type === 'oil_slick') ?? []) {
    alerts.push({
      id: `oil-${obs.id}`,
      type: 'Oil Slick Detected',
      domain: 'marine_oil',
      severity: obs.confidence >= 0.8 ? 'high' : 'medium',
      message: `Area ${obs.area_km2.toFixed(2)} km², confidence ${Math.round(obs.confidence * 100)}%`,
      time: obs.created_at,
      icon: Droplets,
    })
  }

  // Sort most recent first
  alerts.sort((a, b) => b.time.localeCompare(a.time))

  const severityCounts = {
    extreme: alerts.filter((a) => a.severity === 'extreme').length,
    high:    alerts.filter((a) => a.severity === 'high').length,
    medium:  alerts.filter((a) => a.severity === 'medium').length,
    low:     alerts.filter((a) => a.severity === 'low').length,
  }

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Bell className="h-4 w-4 text-slate-400" />
        <h2 className="text-sm font-semibold text-slate-200">Alert History</h2>
        <div className="flex gap-1.5 ml-auto">
          {severityCounts.extreme > 0 && <Badge variant="danger">{severityCounts.extreme} extreme</Badge>}
          {severityCounts.high    > 0 && <Badge variant="danger">{severityCounts.high} high</Badge>}
          {severityCounts.medium  > 0 && <Badge variant="warning">{severityCounts.medium} medium</Badge>}
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {alerts.length === 0 ? (
            <EmptyState
              icon={Bell}
              title="No active alerts"
              description="Alerts are generated when flood risk is elevated, acid risk exceeds 7.0, or oil slicks are confirmed."
              className="py-12"
            />
          ) : (
            <div className="divide-y divide-slate-800">
              {alerts.map((alert) => {
                const Icon = alert.icon
                return (
                  <div key={alert.id} className="flex items-start gap-3 px-4 py-3">
                    <div className="mt-0.5 shrink-0">
                      <Icon className="h-4 w-4 text-slate-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-xs font-medium text-slate-200">{alert.type}</p>
                        <RiskLevelBadge level={alert.severity} />
                        <Badge variant="muted" className="text-[9px]">{alert.domain}</Badge>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">{alert.message}</p>
                      <p className="text-[10px] text-slate-600 mt-0.5">{formatDate(alert.time)}</p>
                    </div>
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
