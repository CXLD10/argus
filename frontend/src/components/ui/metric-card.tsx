import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: LucideIcon
  iconColor?: string
  trend?: { value: string; direction?: 'up' | 'down' | 'flat'; positive?: boolean }
  loading?: boolean
  accentColor?: string
  className?: string
  onClick?: () => void
}

function MetricSkeleton() {
  return (
    <div className="relative rounded-xl border border-slate-800 bg-[#0f1623] p-4 overflow-hidden">
      <div className="h-1.5 w-full bg-[#141d2e] absolute top-0 left-0 right-0 rounded-t-xl" />
      <div className="flex items-start justify-between pt-1">
        <div className="skeleton h-3 w-24 rounded-sm" />
        <div className="skeleton h-8 w-8 rounded-lg" />
      </div>
      <div className="mt-3 space-y-1.5">
        <div className="skeleton h-8 w-20 rounded-sm" />
        <div className="skeleton h-3 w-16 rounded-sm" />
      </div>
    </div>
  )
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconColor = '#3b82f6',
  trend,
  loading,
  accentColor,
  className,
  onClick,
}: MetricCardProps) {
  if (loading) return <MetricSkeleton />

  const TrendIcon = trend?.direction === 'up' ? TrendingUp
    : trend?.direction === 'down' ? TrendingDown
    : Minus

  const trendColor = trend?.positive
    ? 'text-green-400'
    : trend?.positive === false
      ? 'text-red-400'
      : 'text-slate-500'

  return (
    <div
      className={cn(
        'relative rounded-xl border border-slate-800 bg-[#0f1623] p-4 overflow-hidden',
        'transition-all duration-200',
        onClick && 'cursor-pointer hover:border-slate-700 hover:shadow-[0_4px_16px_rgba(0,0,0,0.4)] hover:-translate-y-px',
        className,
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Accent bar */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5 rounded-t-xl opacity-60"
        style={{ background: accentColor ?? iconColor }}
      />

      <div className="flex items-start justify-between">
        <p className="text-label text-slate-500">{title}</p>
        {Icon && (
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg shrink-0"
            style={{ background: `${iconColor}14`, color: iconColor }}
          >
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>

      <div className="mt-2.5">
        <p className="text-[28px] font-bold text-slate-50 tabular-nums leading-none tracking-tight">
          {value}
        </p>
        <div className="mt-1.5 flex items-center gap-2 min-h-[18px]">
          {trend && (
            <span className={cn('flex items-center gap-1 text-micro font-medium', trendColor)}>
              <TrendIcon className="h-3 w-3" />
              {trend.value}
            </span>
          )}
          {subtitle && (
            <span className="text-micro text-slate-500">{subtitle}</span>
          )}
        </div>
      </div>
    </div>
  )
}
