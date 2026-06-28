import { useQuery } from '@tanstack/react-query'
import { fetchObservations, fetchFloodRisk, fetchAcidRisk, fetchChokePoints } from '@/api/endpoints'
import { useAOIStore } from '@/store/aoiStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FileDown, Download, FileText, Database } from 'lucide-react'

function downloadJSON(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function ExportsPage() {
  const { selectedAOI } = useAOIStore()
  const aoiId = selectedAOI?.id ?? ''

  const { data: obsData }   = useQuery({ queryKey: ['obs', aoiId], queryFn: () => fetchObservations(aoiId), enabled: !!aoiId })
  const { data: floodData } = useQuery({ queryKey: ['flood', aoiId], queryFn: () => fetchFloodRisk(aoiId), enabled: !!aoiId })
  const { data: acidData }  = useQuery({ queryKey: ['acid', aoiId],  queryFn: () => fetchAcidRisk(aoiId),  enabled: !!aoiId })
  const { data: chokeData } = useQuery({ queryKey: ['choke', aoiId], queryFn: () => fetchChokePoints(aoiId), enabled: !!aoiId })

  const exports = [
    {
      label: 'Observations (GeoJSON)',
      desc: `${obsData?.count ?? 0} records`,
      icon: Database,
      onClick: () => downloadJSON(obsData, `argus-observations-${aoiId}-${Date.now()}.json`),
      disabled: !obsData?.count,
    },
    {
      label: 'Flood Risk Predictions',
      desc: `${floodData?.count ?? 0} predictions`,
      icon: FileText,
      onClick: () => downloadJSON(floodData, `argus-flood-risk-${aoiId}-${Date.now()}.json`),
      disabled: !floodData?.count,
    },
    {
      label: 'Acid Risk Predictions',
      desc: `${acidData?.count ?? 0} predictions`,
      icon: FileText,
      onClick: () => downloadJSON(acidData, `argus-acid-risk-${aoiId}-${Date.now()}.json`),
      disabled: !acidData?.count,
    },
    {
      label: 'Choke Points',
      desc: `${chokeData?.count ?? 0} locations`,
      icon: Database,
      onClick: () => downloadJSON(chokeData, `argus-choke-points-${aoiId}-${Date.now()}.json`),
      disabled: !chokeData?.count,
    },
  ]

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <div className="flex items-center gap-2">
        <FileDown className="h-4 w-4 text-slate-400" />
        <h2 className="text-sm font-semibold text-slate-200">Reports &amp; Exports</h2>
        {selectedAOI && (
          <Badge variant="muted" className="ml-auto">{selectedAOI.name}</Badge>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {exports.map((ex) => {
          const Icon = ex.icon
          return (
            <Card key={ex.label} className={ex.disabled ? 'opacity-50' : ''}>
              <CardContent className="py-4 flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-800">
                  <Icon className="h-4 w-4 text-slate-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-200 leading-tight">{ex.label}</p>
                  <p className="text-[10px] text-slate-500">{ex.desc}</p>
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={ex.onClick}
                  disabled={ex.disabled}
                  className="h-7 w-7 shrink-0"
                >
                  <Download className="h-3.5 w-3.5" />
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card>
        <CardHeader><CardTitle>About Exports</CardTitle></CardHeader>
        <CardContent>
          <p className="text-xs text-slate-400 leading-relaxed">
            All exports are JSON snapshots of the current platform state for the selected AOI.
            GeoJSON geometries are in EPSG:4326 (WGS84). Evidence class is included on every record
            per INV-3. Exports do not include raw satellite imagery — only analysis products.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
