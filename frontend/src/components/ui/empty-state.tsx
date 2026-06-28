import { cn } from '@/lib/utils'
import { Button } from './button'

interface EmptyStateProps {
  icon?: React.ComponentType<{ className?: string }>
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
  compact?: boolean
  className?: string
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  compact = false,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center',
        compact ? 'gap-2 py-8 px-4' : 'gap-3 py-12 px-6',
        className,
      )}
    >
      {Icon && (
        <div
          className={cn(
            'flex items-center justify-center rounded-xl bg-[#141d2e] border border-slate-800',
            compact ? 'h-10 w-10' : 'h-12 w-12',
          )}
        >
          <Icon className={cn('text-slate-500', compact ? 'h-5 w-5' : 'h-6 w-6')} />
        </div>
      )}
      <div className={cn('space-y-1', compact ? 'max-w-[180px]' : 'max-w-[260px]')}>
        <p className={cn('font-medium text-slate-300', compact ? 'text-xs' : 'text-sm')}>
          {title}
        </p>
        {description && (
          <p className={cn('text-slate-500 leading-relaxed', compact ? 'text-[11px]' : 'text-xs')}>
            {description}
          </p>
        )}
      </div>
      {action && (
        <Button variant="outline" size="sm" onClick={action.onClick} className="mt-1">
          {action.label}
        </Button>
      )}
    </div>
  )
}
