import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import type { ObservationSchema } from '@/api/types'
import { formatDateShort } from '@/lib/utils'
import { EmptyState } from '@/components/ui/empty-state'
import { TrendingUp } from 'lucide-react'

interface Props {
  observations: ObservationSchema[]
  obsType?: string
  threshold?: number
  thresholdLabel?: string
}

export function WQTrendChart({ observations, obsType = 'chlorophyll_a', threshold, thresholdLabel }: Props) {
  const data = observations
    .filter((o) => o.obs_type === obsType && o.value != null)
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .slice(-30)
    .map((o) => ({
      date: formatDateShort(o.created_at),
      value: Number(o.value?.toFixed(2)),
      confidence: o.confidence,
    }))

  if (data.length === 0) {
    return (
      <EmptyState
        icon={TrendingUp}
        title="No observations"
        description="No data for the selected period."
      />
    )
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: -24, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2d45" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: '#475569', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: '#475569', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          width={40}
        />
        {threshold != null && (
          <ReferenceLine
            y={threshold}
            stroke="#ef4444"
            strokeDasharray="4 3"
            label={{ value: thresholdLabel ?? `${threshold}`, fill: '#ef4444', fontSize: 10 }}
          />
        )}
        <Tooltip
          contentStyle={{
            background: '#1a2235', border: '1px solid #1e2d45',
            borderRadius: 8, fontSize: 12, color: '#f1f5f9',
          }}
          labelStyle={{ color: '#94a3b8' }}
          formatter={(v: unknown) => [(v as number).toFixed(2), obsType.replace(/_/g, ' ')]}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#3b82f6"
          strokeWidth={1.5}
          dot={false}
          activeDot={{ r: 4, fill: '#3b82f6', stroke: '#0a0e17', strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
