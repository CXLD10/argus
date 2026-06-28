import { cn } from '@/lib/utils'
import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
type Size    = 'sm' | 'md' | 'lg' | 'icon'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
}

const variantClasses: Record<Variant, string> = {
  primary:   'bg-blue-600 hover:bg-blue-500 text-white shadow-sm',
  secondary: 'bg-slate-700 hover:bg-slate-600 text-slate-100 border border-slate-600',
  ghost:     'hover:bg-slate-800 text-slate-300 hover:text-slate-100',
  danger:    'bg-red-600 hover:bg-red-500 text-white',
  outline:   'border border-slate-700 hover:bg-slate-800 text-slate-300 hover:text-slate-100',
}

const sizeClasses: Record<Size, string> = {
  sm:   'h-7 px-2.5 text-xs rounded-md gap-1.5',
  md:   'h-8 px-3 text-sm rounded-md gap-2',
  lg:   'h-10 px-4 text-sm rounded-lg gap-2',
  icon: 'h-8 w-8 rounded-md',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center font-medium transition-colors',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.37 0 0 5.37 0 12h4z"/>
        </svg>
      )}
      {children}
    </button>
  )
}
