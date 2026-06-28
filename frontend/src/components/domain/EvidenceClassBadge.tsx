import { Badge } from '@/components/ui/badge'
import type { EvidenceClass } from '@/api/types'

interface Props { value: EvidenceClass | string }

export function EvidenceClassBadge({ value }: Props) {
  if (value === 'measured')
    return <Badge variant="success">measured</Badge>
  if (value === 'modeled')
    return <Badge variant="warning">modeled</Badge>
  return <Badge variant="muted">inferred</Badge>
}
