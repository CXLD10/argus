import { cn, acidRiskColor, riskColor } from '@/lib/utils'
import type { RiskLevel } from '@/api/types'

interface FloodGaugeProps {
  score: number   // 0–1
  level: RiskLevel | null
  label?: string
}

export function FloodRiskGauge({ score, level, label = 'Flood Risk Score' }: FloodGaugeProps) {
  const pct = Math.round(score * 100)
  const color = riskColor(level)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400">{label}</p>
        <p className="text-sm font-semibold" style={{ color }}>{pct}%</p>
      </div>
      <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  )
}

interface AcidGaugeProps {
  index: number   // 0–10
  label?: string
}

export function AcidRiskGauge({ index, label = 'Acid Risk Index' }: AcidGaugeProps) {
  const pct = Math.round((index / 10) * 100)
  const color = acidRiskColor(index)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400">{label}</p>
        <p className="text-sm font-semibold tabular-nums" style={{ color }}>
          {index.toFixed(1)}<span className="text-xs text-slate-500">/10</span>
        </p>
      </div>
      <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: `linear-gradient(90deg, #22c55e, ${color})` }}
        />
      </div>
    </div>
  )
}
