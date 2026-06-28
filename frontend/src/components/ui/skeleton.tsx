import { cn } from '@/lib/utils'

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('skeleton rounded', className)} {...props} />
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn('rounded-xl border border-slate-800 bg-[#0f1623] p-4 space-y-3', className)}>
      <Skeleton className="h-3 w-1/3" />
      <Skeleton className="h-8 w-14" />
      <Skeleton className="h-3 w-24" />
    </div>
  )
}

export function SkeletonMetricRow() {
  return (
    <div className="grid grid-cols-4 gap-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

export function SkeletonListItem({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-3 py-2.5 px-3', className)}>
      <Skeleton className="h-8 w-8 rounded-lg shrink-0" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-3 w-3/4" />
        <Skeleton className="h-2.5 w-1/2" />
      </div>
      <Skeleton className="h-5 w-12 rounded-full shrink-0" />
    </div>
  )
}

export function SkeletonTableRow({ cols = 4 }: { cols?: number }) {
  return (
    <div className="flex items-center gap-4 py-3 px-4">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className={`h-3 ${i === 0 ? 'w-32' : i === cols - 1 ? 'w-16' : 'flex-1'}`} />
      ))}
    </div>
  )
}

export function SkeletonChart({ height = 180 }: { height?: number }) {
  return (
    <div className="space-y-2">
      <div className="flex items-end gap-2" style={{ height }}>
        {Array.from({ length: 12 }).map((_, i) => {
          const h = 20 + Math.random() * 80
          return (
            <div key={i} className="flex-1 skeleton rounded-sm" style={{ height: `${h}%` }} />
          )
        })}
      </div>
      <div className="flex gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-2.5 w-8" />
        ))}
      </div>
    </div>
  )
}
