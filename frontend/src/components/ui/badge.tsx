import { cn } from '@/lib/utils'

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'muted' | 'outline' | 'ghost'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: Variant
}

const variantClasses: Record<Variant, string> = {
  default:  'bg-blue-500/15 text-blue-400 border-blue-500/25',
  success:  'bg-green-500/15 text-green-400 border-green-500/25',
  warning:  'bg-amber-500/15 text-amber-400 border-amber-500/25',
  danger:   'bg-red-500/15 text-red-400 border-red-500/25',
  info:     'bg-sky-500/15 text-sky-400 border-sky-500/25',
  muted:    'bg-slate-500/10 text-slate-400 border-slate-500/20',
  outline:  'bg-transparent text-slate-300 border-slate-600',
  ghost:    'bg-transparent text-slate-400 border-transparent',
}

export function Badge({ variant = 'default', className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}
