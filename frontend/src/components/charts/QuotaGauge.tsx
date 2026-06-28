import { formatBytes } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface Props {
  used: number
  limit: number
  label: string
  unit?: string
  warning?: number  // fraction (0-1) at which to show warning color
}

export function QuotaGauge({ used, limit, label, unit = 'bytes', warning = 0.8 }: Props) {
  const pct = limit > 0 ? Math.min(1, used / limit) : 0
  const over = pct >= warning
  const barColor = pct >= 1 ? '#ef4444' : over ? '#f59e0b' : '#22c55e'

  const fmt = unit === 'bytes' ? formatBytes : (n: number) => n.toLocaleString()

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400">{label}</p>
        <p className={cn('text-xs font-medium tabular-nums', over ? 'text-amber-400' : 'text-slate-300')}>
          {fmt(used)} / {fmt(limit)}
        </p>
      </div>
      <div className="h-1 w-full rounded-full bg-slate-800 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct * 100}%`, background: barColor }}
        />
      </div>
    </div>
  )
}
