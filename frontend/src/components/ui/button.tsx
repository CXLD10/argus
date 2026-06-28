import { cn } from '@/lib/utils'
import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline' | 'link'
type Size    = 'xs' | 'sm' | 'md' | 'lg' | 'icon'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
}

const variantClasses: Record<Variant, string> = {
  primary:   'bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white shadow-sm shadow-blue-900/30',
  secondary: 'bg-[#141d2e] hover:bg-[#1a2436] active:bg-[#0f1623] text-slate-200 border border-slate-700',
  ghost:     'hover:bg-[#141d2e] active:bg-[#0f1623] text-slate-400 hover:text-slate-200',
  danger:    'bg-red-600 hover:bg-red-500 active:bg-red-700 text-white',
  outline:   'border border-slate-700 hover:border-slate-600 hover:bg-[#141d2e] text-slate-300 hover:text-slate-100',
  link:      'text-blue-400 hover:text-blue-300 underline-offset-2 hover:underline',
}

const sizeClasses: Record<Size, string> = {
  xs:   'h-6 px-2 text-[11px] rounded-md gap-1',
  sm:   'h-7 px-2.5 text-xs rounded-md gap-1.5',
  md:   'h-8 px-3 text-sm rounded-lg gap-2',
  lg:   'h-10 px-4 text-sm rounded-lg gap-2',
  icon: 'h-8 w-8 rounded-lg flex-shrink-0',
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
        'inline-flex items-center justify-center font-medium transition-all duration-150',
        'disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 focus-visible:ring-offset-[#080c14]',
        'select-none',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-3 w-3 shrink-0" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.37 0 0 5.37 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  )
}
