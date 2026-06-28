import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'
import { Skeleton } from './skeleton'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: LucideIcon
  iconColor?: string
  trend?: { value: string; positive?: boolean }
  loading?: boolean
  className?: string
}

export function MetricCard({
  title, value, subtitle, icon: Icon, iconColor = '#3b82f6',
  trend, loading, className,
}: MetricCardProps) {
  if (loading) {
    return (
      <div className={cn('rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3', className)}>
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-16" />
        <Skeleton className="h-3 w-20" />
      </div>
    )
  }

  return (
    <div
      className={cn(
        'rounded-xl border border-slate-800 bg-slate-900 p-4',
        'hover:border-slate-700 transition-colors group',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wider leading-none">
          {title}
        </p>
        {Icon && (
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
            style={{ background: `${iconColor}18`, color: iconColor }}
          >
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      <div className="mt-3">
        <p className="text-2xl font-semibold text-slate-50 tabular-nums leading-none">
          {value}
        </p>
        {(subtitle || trend) && (
          <div className="mt-1.5 flex items-center gap-2">
            {trend && (
              <span
                className={cn(
                  'text-xs font-medium',
                  trend.positive ? 'text-green-400' : 'text-red-400',
                )}
              >
                {trend.value}
              </span>
            )}
            {subtitle && <span className="text-xs text-slate-500">{subtitle}</span>}
          </div>
        )}
      </div>
    </div>
  )
}
