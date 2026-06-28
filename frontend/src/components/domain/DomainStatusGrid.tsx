import { useQuery } from '@tanstack/react-query'
import { fetchStatus } from '@/api/endpoints'
import { DOMAIN_LABELS, DOMAIN_COLORS, timeAgo } from '@/lib/utils'
import { cn } from '@/lib/utils'

export function DomainStatusGrid() {
  const { data } = useQuery({
    queryKey: ['status'],
    queryFn: fetchStatus,
    refetchInterval: 60_000,
  })

  const runs = data?.domain_runs ?? []
  const domains = ['marine_oil', 'inland_wq', 'weather_hydro', 'hydro_chokepoints']

  return (
    <div className="grid grid-cols-2 gap-2">
      {domains.map((domainId) => {
        const run = runs.filter((r) => r.domain_id === domainId).sort(
          (a, b) => (b.last_run_at ?? '').localeCompare(a.last_run_at ?? ''),
        )[0]
        const color = DOMAIN_COLORS[domainId]
        const isOk = run?.last_run_status === 'complete'

        return (
          <div
            key={domainId}
            className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2"
          >
            <div
              className="h-2 w-2 rounded-full shrink-0"
              style={{ background: run ? (isOk ? '#22c55e' : '#ef4444') : '#334155' }}
            />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-slate-200 truncate">
                {DOMAIN_LABELS[domainId] ?? domainId}
              </p>
              <p className="text-[10px] text-slate-500">
                {run ? timeAgo(run.last_run_at) : 'Never run'}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
