import { useQuery } from '@tanstack/react-query'
import { fetchAOIs, fetchStatus } from '@/api/endpoints'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { DomainStatusGrid } from '@/components/domain/DomainStatusGrid'
import { QuotaGauge } from '@/components/charts/QuotaGauge'
import { ShieldCheck, Database, Activity } from 'lucide-react'
import { formatDate } from '@/lib/utils'

export function AdminPage() {
  const { data: aoiData } = useQuery({
    queryKey: ['aois'],
    queryFn: fetchAOIs,
  })

  const { data: statusData } = useQuery({
    queryKey: ['status'],
    queryFn: fetchStatus,
    refetchInterval: 30_000,
  })

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-slate-400" />
        <h2 className="text-sm font-semibold text-slate-200">Administration</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* System status */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-3.5 w-3.5 text-green-400" />
                System Status
              </CardTitle>
              {statusData && (
                <Badge variant={statusData.store_accessible ? 'success' : 'danger'}>
                  {statusData.store_accessible ? 'Online' : 'Degraded'}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {statusData && (
              <>
                <div className="grid grid-cols-2 gap-y-2 text-xs">
                  <span className="text-slate-500">Version</span>
                  <span className="text-slate-200 font-mono">{statusData.version}</span>
                  <span className="text-slate-500">Store accessible</span>
                  <span className="text-slate-200">{statusData.store_accessible ? 'Yes' : 'No'}</span>
                  <span className="text-slate-500">Last run</span>
                  <span className="text-slate-200">
                    {statusData.last_analysis_run_at ? formatDate(statusData.last_analysis_run_at) : 'Never'}
                  </span>
                  <span className="text-slate-500">Open-Meteo calls</span>
                  <span className="text-slate-200">{statusData.open_meteo_calls_today.toLocaleString()} / 10,000</span>
                </div>
                <div className="space-y-2 pt-2 border-t border-slate-800">
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
              </>
            )}
          </CardContent>
        </Card>

        {/* Domain runs */}
        <Card>
          <CardHeader>
            <CardTitle>Domain Run Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <DomainStatusGrid />
            {statusData && statusData.domain_runs.length > 0 && (
              <div className="mt-3 space-y-0 border-t border-slate-800 pt-3">
                {statusData.domain_runs.map((run) => (
                  <div key={run.domain_id} className="flex items-start justify-between py-2 border-b border-slate-800 last:border-0">
                    <div>
                      <p className="text-xs font-medium text-slate-200">{run.domain_id}</p>
                      <p className="text-[10px] text-slate-500">
                        {run.observations_created} obs · {run.scenes_fetched} scenes
                      </p>
                    </div>
                    <div className="text-right">
                      <Badge variant={run.last_run_status === 'ok' ? 'success' : 'warning'}>
                        {run.last_run_status ?? 'never'}
                      </Badge>
                      <p className="text-[10px] text-slate-600 mt-0.5">
                        {run.last_run_at ? formatDate(run.last_run_at) : '—'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* AOI list */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Database className="h-3.5 w-3.5 text-blue-400" />
                Areas of Interest
              </CardTitle>
              <Badge variant="muted">{aoiData?.count ?? 0} total</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {(aoiData?.items ?? []).length === 0 ? (
              <p className="text-xs text-slate-500">No AOIs configured.</p>
            ) : (
              <div className="divide-y divide-slate-800">
                {aoiData?.items.map((aoi) => (
                  <div key={aoi.id} className="flex items-center justify-between py-2.5">
                    <div>
                      <p className="text-sm font-medium text-slate-200">{aoi.name}</p>
                      <p className="text-[10px] font-mono text-slate-500">{aoi.id}</p>
                      <p className="text-[10px] text-slate-600">{aoi.domains.join(', ')}</p>
                    </div>
                    <Badge variant={aoi.active ? 'success' : 'muted'}>
                      {aoi.active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
