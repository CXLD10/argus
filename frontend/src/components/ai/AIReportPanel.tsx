import { useQuery } from '@tanstack/react-query'
import { fetchWQReport } from '@/api/endpoints'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Bot, BookOpen, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'

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
    <div className={cn('rounded-xl border border-slate-800 bg-slate-900', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
        <div className="flex h-6 w-6 items-center justify-center rounded bg-blue-600/20">
          <Bot className="h-3.5 w-3.5 text-blue-400" />
        </div>
        <p className="text-sm font-medium text-slate-200">AI Situation Report</p>
        <Badge variant="info" className="ml-auto text-[10px]">Advisory</Badge>
      </div>

      <div className="p-4">
        {isLoading && (
          <div className="space-y-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
            <Skeleton className="h-3 w-4/5" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-3/4" />
          </div>
        )}

        {isError && (
          <p className="text-xs text-slate-500 italic">
            AI report unavailable. Grounded template may be shown when backend is live.
          </p>
        )}

        {data && (
          <div className="space-y-3">
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
              {data.text}
            </p>

            {data.citations.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {data.citations.map((c, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-mono
                      bg-blue-500/10 text-blue-400 border border-blue-500/20 cursor-default"
                    title={c}
                  >
                    <BookOpen className="h-2.5 w-2.5" />
                    {c.slice(0, 8)}…
                  </span>
                ))}
              </div>
            )}

            {data._attribution && (
              <p className="text-[10px] text-slate-600 pt-1 border-t border-slate-800">
                {data._attribution} · Model: {data.model}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
