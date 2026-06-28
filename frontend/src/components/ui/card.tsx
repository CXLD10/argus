import { cn } from '@/lib/utils'

type CardVariant = 'default' | 'elevated' | 'interactive' | 'inset' | 'ghost'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant
}

const cardVariants: Record<CardVariant, string> = {
  default:     'rounded-xl border border-slate-800 bg-[#0f1623] text-slate-100',
  elevated:    'rounded-xl border border-slate-800 bg-[#0f1623] text-slate-100 shadow-[0_4px_16px_rgba(0,0,0,0.4),0_2px_4px_rgba(0,0,0,0.3)]',
  interactive: 'rounded-xl border border-slate-800 bg-[#0f1623] text-slate-100 card-interactive cursor-pointer',
  inset:       'rounded-lg border border-slate-800/60 bg-[#080c14] text-slate-100',
  ghost:       'rounded-xl bg-transparent text-slate-100',
}

export function Card({ className, variant = 'default', children, ...props }: CardProps) {
  return (
    <div
      className={cn(cardVariants[variant], className)}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex flex-col gap-1 px-4 pt-4 pb-2', className)} {...props}>
      {children}
    </div>
  )
}

export function CardTitle({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={cn('text-sm font-semibold text-slate-200 leading-none tracking-tight', className)} {...props}>
      {children}
    </h3>
  )
}

export function CardDescription({ className, children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn('text-xs text-slate-500', className)} {...props}>
      {children}
    </p>
  )
}

export function CardContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-4 pb-4 pt-2', className)} {...props}>
      {children}
    </div>
  )
}

export function CardFooter({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex items-center px-4 pb-4 pt-0 gap-2', className)} {...props}>
      {children}
    </div>
  )
}

export function CardSeparator() {
  return <div className="h-px bg-slate-800/60 mx-4" />
}
