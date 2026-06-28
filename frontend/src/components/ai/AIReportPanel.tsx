import { useQuery } from '@tanstack/react-query'
import { fetchWQReport } from '@/api/endpoints'
import { Skeleton } from '@/components/ui/skeleton'
import { Sparkles, Lock, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'

interface Props {
  targetId: string
  className?: string
}

export function AIReportPanel({ targetId, className }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['wq-report', targetId],
    queryFn: () => fetchWQReport(targetId),
    staleTime: 300_000,
  })

  return (
    <Card className={cn('overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-slate-800/60">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-600/15">
          <Sparkles className="h-3.5 w-3.5 text-blue-400" />
        </div>
        <p className="text-sm font-semibold text-slate-200 flex-1">AI Situation Report</p>
        <div className="flex items-center gap-1 text-[10px] text-slate-600">
          <Lock className="h-2.5 w-2.5" />
          Advisory
        </div>
      </div>

      <CardContent className="pt-3">
        {isLoading && (
          <div className="space-y-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-11/12" />
            <Skeleton className="h-3 w-4/5" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-2/3" />
          </div>
        )}

        {isError && (
          <p className="text-xs text-slate-600 italic py-2">
            Report unavailable — backend service not reachable.
          </p>
        )}

        {data && (
          <div className="space-y-3">
            <p className="text-sm text-slate-300 leading-relaxed">
              {data.text}
            </p>

            {data.citations.length > 0 && (
              <div className="pt-2 border-t border-slate-800/60">
                <p className="text-label text-slate-600 mb-2">Sources</p>
                <div className="space-y-1">
                  {data.citations.map((c, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-[11px] text-slate-500 group"
                      title={c}
                    >
                      <span className="citation-badge shrink-0">{i + 1}</span>
                      <span className="font-mono truncate group-hover:text-slate-400 transition-colors">
                        {c}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {data._attribution && (
              <p className="text-[10px] text-slate-700 pt-1 border-t border-slate-800/40">
                {data._attribution}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
