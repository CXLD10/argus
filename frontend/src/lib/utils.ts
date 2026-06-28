import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { RiskLevel } from '@/api/types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Format bytes to MB or GB */
export function formatBytes(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(2)} GB`
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(0)} KB`
  return `${bytes} B`
}

/** Format ISO timestamp to human-readable */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function formatDateShort(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric',
  })
}

/** Time since ISO timestamp */
export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '—'
  const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (secs < 60) return `${secs}s ago`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`
  return `${Math.floor(secs / 86400)}d ago`
}

/** Confidence → color class */
export function confidenceColor(conf: number): string {
  if (conf >= 0.8) return '#ef4444'
  if (conf >= 0.5) return '#f97316'
  return '#facc15'
}

/** Risk level → color */
export const RISK_COLORS: Record<RiskLevel, string> = {
  low:     '#22c55e',
  medium:  '#f59e0b',
  high:    '#f97316',
  extreme: '#ef4444',
}

export function riskColor(level: RiskLevel | null | undefined): string {
  if (!level) return '#475569'
  return RISK_COLORS[level] ?? '#475569'
}

/** Evidence class badge variant */
export function evidenceBadgeVariant(ev: string): 'success' | 'warning' | 'muted' {
  if (ev === 'measured')  return 'success'
  if (ev === 'modeled')   return 'warning'
  return 'muted'
}

/** Domain → display label */
export const DOMAIN_LABELS: Record<string, string> = {
  marine_oil:          'Marine Oil (D1)',
  inland_wq:           'Water Quality (D2)',
  weather_hydro:       'Weather / Hydro (D3)',
  hydro_chokepoints:   'Choke Points (D4)',
}

export const DOMAIN_COLORS: Record<string, string> = {
  marine_oil:         '#f97316',
  inland_wq:          '#3b82f6',
  weather_hydro:      '#38bdf8',
  hydro_chokepoints:  '#a78bfa',
}

/** Acid risk index → color */
export function acidRiskColor(index: number): string {
  if (index >= 7) return '#ef4444'
  if (index >= 4) return '#f97316'
  if (index >= 2) return '#f59e0b'
  return '#22c55e'
}

/** Truncate string */
export function truncate(str: string, max: number): string {
  return str.length > max ? str.slice(0, max) + '…' : str
}

/** Clamp number */
export function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val))
}
