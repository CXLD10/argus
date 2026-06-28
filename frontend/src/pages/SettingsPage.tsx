import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Settings, Info } from 'lucide-react'

const CONFIG_ITEMS = [
  { key: 'ARGUS_ENV', value: 'development', desc: 'Runtime environment flag' },
  { key: 'API base URL', value: 'http://localhost:8000', desc: 'Backend API endpoint' },
  { key: 'Tailwind', value: 'v4 (CSS theme)', desc: '@tailwindcss/vite plugin' },
  { key: 'shadcn/ui', value: 'New York, Neutral', desc: 'Component style preset' },
]

export function SettingsPage() {
  return (
    <div className="h-full overflow-y-auto p-4 space-y-4 page-enter">
      <div className="flex items-center gap-2">
        <Settings className="h-4 w-4 text-slate-400" />
        <h2 className="text-sm font-semibold text-slate-200">Settings</h2>
        <Badge variant="muted" className="ml-auto">Read-only (dev)</Badge>
      </div>

      <Card className="border-blue-500/20 bg-blue-500/5">
        <CardContent className="py-3 flex items-start gap-2">
          <Info className="h-3.5 w-3.5 text-blue-400 mt-0.5 shrink-0" />
          <p className="text-xs text-slate-400 leading-relaxed">
            Production config (GCP Cloud Run, GCS artifact store, Secret Manager) is governed by
            ARGUS_ENV=production flag and ADR-0008. These settings are read-only in development.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Environment Configuration</CardTitle></CardHeader>
        <CardContent>
          <div className="divide-y divide-slate-800">
            {CONFIG_ITEMS.map((item) => (
              <div key={item.key} className="flex items-center justify-between py-2.5">
                <div>
                  <p className="text-xs font-medium text-slate-200 font-mono">{item.key}</p>
                  <p className="text-[10px] text-slate-500">{item.desc}</p>
                </div>
                <span className="text-xs text-slate-300 font-mono bg-slate-800 px-2 py-0.5 rounded">
                  {item.value}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Data Source Quotas</CardTitle></CardHeader>
        <CardContent>
          <div className="divide-y divide-slate-800">
            {[
              { name: 'CDSE (Copernicus)', limit: '1 GB / day', note: 'General user tier' },
              { name: 'Open-Meteo', limit: '10,000 calls / day', note: 'Free, CC BY 4.0' },
              { name: 'Copernicus DEM', limit: 'Unlimited (static)', note: 'Downloaded once per AOI' },
              { name: 'CMEMS', limit: 'Free tier', note: 'Monthly product pull' },
              { name: 'Anthropic API', limit: 'Educational/free', note: 'Degrades to templated reports over budget' },
            ].map((q) => (
              <div key={q.name} className="py-2.5">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-slate-200">{q.name}</p>
                  <Badge variant="muted">{q.limit}</Badge>
                </div>
                <p className="text-[10px] text-slate-500 mt-0.5">{q.note}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
