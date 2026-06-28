import { Badge } from '@/components/ui/badge'
import type { RiskLevel } from '@/api/types'

// Can't import Variant as it's internal, so we inline
const LEVEL_VARIANT: Record<RiskLevel, string> = {
  low:     'success',
  medium:  'warning',
  high:    'danger',
  extreme: 'danger',
}

const LEVEL_LABEL: Record<RiskLevel, string> = {
  low:     'Low',
  medium:  'Medium',
  high:    'High',
  extreme: 'Extreme',
}

interface Props {
  level: RiskLevel | null | undefined
  showDot?: boolean
}

export function RiskLevelBadge({ level, showDot }: Props) {
  if (!level) return <Badge variant="muted">—</Badge>
  return (
    <Badge variant={LEVEL_VARIANT[level] as 'success' | 'warning' | 'danger'}>
      {showDot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {LEVEL_LABEL[level]}
    </Badge>
  )
}
