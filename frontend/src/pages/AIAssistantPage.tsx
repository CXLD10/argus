import { useQuery } from '@tanstack/react-query'
import { fetchWaterbodies } from '@/api/endpoints'
import { NLQueryBox } from '@/components/ai/NLQueryBox'
import { AIReportPanel } from '@/components/ai/AIReportPanel'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bot, Info } from 'lucide-react'
import { useState } from 'react'

export function AIAssistantPage() {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null)

  const { data: wbData } = useQuery({
    queryKey: ['waterbodies'],
    queryFn: fetchWaterbodies,
  })

  const targetId = selectedTarget ?? wbData?.target_ids?.[0] ?? ''

  return (
    <div className="flex h-full overflow-hidden page-enter">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col overflow-hidden p-4 space-y-4">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-blue-400" />
          <h2 className="text-sm font-semibold text-slate-200">AI Environmental Assistant</h2>
          <Badge variant="warning" className="ml-auto">Advisory — Human-in-the-loop</Badge>
        </div>

        <Card className="border-blue-500/20 bg-blue-500/5">
          <CardContent className="py-3 flex items-start gap-2">
            <Info className="h-3.5 w-3.5 text-blue-400 mt-0.5 shrink-0" />
            <p className="text-xs text-slate-400 leading-relaxed">
              The AI assistant is grounded in platform data only. Every factual claim cites an observation
              or prediction record. Write actions (domain runs, config changes) are refused. All outputs
              are advisory and require human review before operational use.
            </p>
          </CardContent>
        </Card>

        <NLQueryBox className="flex-1" />
      </div>

      {/* Right: AI reports panel */}
      <div className="w-80 border-l border-slate-800 bg-slate-950 overflow-y-auto p-4 space-y-4">
        <div>
          <p className="text-xs font-semibold text-slate-400 mb-2">Situation Reports</p>
          {(wbData?.target_ids ?? []).length === 0 && (
            <p className="text-[11px] text-slate-600">No water bodies found. Run inland_wq domain first.</p>
          )}
          {(wbData?.target_ids ?? []).map((id) => (
            <button
              key={id}
              onClick={() => setSelectedTarget(id)}
              className={`w-full text-left mb-1 rounded-lg px-3 py-2 text-[11px] transition-colors ${
                (selectedTarget ?? wbData?.target_ids?.[0]) === id
                  ? 'bg-blue-600/20 text-blue-300'
                  : 'bg-slate-900 text-slate-500 hover:text-slate-300 border border-slate-800'
              }`}
            >
              {id.slice(0, 28)}…
            </button>
          ))}
        </div>

        {targetId && (
          <AIReportPanel targetId={targetId} />
        )}
      </div>
    </div>
  )
}
