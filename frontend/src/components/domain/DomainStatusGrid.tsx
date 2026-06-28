import { useQuery } from '@tanstack/react-query'
import { fetchStatus } from '@/api/endpoints'
import { DOMAIN_LABELS, DOMAIN_COLORS, timeAgo } from '@/lib/utils'
import { cn } from '@/lib/utils'

const DOMAINS = [
  { id: 'marine_oil',        short: 'D1' },
  { id: 'inland_wq',         short: 'D2' },
  { id: 'weather_hydro',     short: 'D3' },
  { id: 'hydro_chokepoints', short: 'D4' },
]

export function DomainStatusGrid() {
  const { data } = useQuery({
    queryKey: ['status'],
    queryFn: fetchStatus,
    refetchInterval: 60_000,
  })

  const runs = data?.domain_runs ?? []

  return (
    <div className="grid grid-cols-2 gap-1.5">
      {DOMAINS.map(({ id, short }) => {
        const run = runs
          .filter((r) => r.domain_id === id)
          .sort((a, b) => (b.last_run_at ?? '').localeCompare(a.last_run_at ?? ''))[0]

        const color = DOMAIN_COLORS[id]
        const status = !run ? 'idle' : run.last_run_status === 'complete' ? 'ok' : 'error'

        return (
          <div
            key={id}
            className={cn(
              'relative flex items-center gap-2.5 rounded-lg px-2.5 py-2',
              'border bg-[#080c14] transition-colors',
              status === 'ok'    && 'border-green-900/40',
              status === 'error' && 'border-red-900/40',
              status === 'idle'  && 'border-[#0f1a2a]',
            )}
          >
            {/* Domain color accent */}
            <div
              className="absolute left-0 top-2 bottom-2 w-0.5 rounded-r"
              style={{ background: status !== 'idle' ? color : '#1e293b' }}
            />

            <div className={cn(
              'h-1.5 w-1.5 rounded-full shrink-0 ml-1',
              status === 'ok'    && 'bg-green-400 shadow-[0_0_6px_rgba(34,197,94,0.4)]',
              status === 'error' && 'bg-red-400',
              status === 'idle'  && 'bg-slate-700',
            )} />

            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-slate-300 truncate leading-none">
                {DOMAIN_LABELS[id]?.split(' ')[0] ?? short}
              </p>
              <p className="text-[10px] text-slate-600 leading-none mt-0.5">
                {run ? timeAgo(run.last_run_at) : 'Never run'}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
