import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, GeoJSON, CircleMarker, LayerGroup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { AOISchema, ObservationSchema, ChokePointSchema, ForecastFrameSchema } from '@/api/types'
import { confidenceColor, riskColor } from '@/lib/utils'
import type { RiskLevel } from '@/api/types'
import L from 'leaflet'

// Fix default Leaflet icon paths
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

interface ArgusMapProps {
  aoi?: AOISchema
  observations?: ObservationSchema[]
  chokePoints?: ChokePointSchema[]
  trajectoryFrames?: ForecastFrameSchema[]
  floodRiskLevel?: RiskLevel | null
  activeLayers?: Set<string>
  onObservationClick?: (obs: ObservationSchema) => void
  className?: string
}

function FlyToAOI({ aoi }: { aoi?: AOISchema }) {
  const map = useMap()
  useEffect(() => {
    if (!aoi) return
    try {
      const layer = L.geoJSON(aoi.geometry as GeoJSON.GeoJsonObject)
      const bounds = layer.getBounds()
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [32, 32], maxZoom: 12 })
    } catch { /* ignore invalid geometries */ }
  }, [aoi, map])
  return null
}

export function ArgusMap({
  aoi,
  observations = [],
  chokePoints = [],
  trajectoryFrames = [],
  floodRiskLevel,
  activeLayers = new Set(['observations', 'choke_points', 'trajectory']),
  onObservationClick,
  className,
}: ArgusMapProps) {
  return (
    <MapContainer
      center={[11.15, -61.25]}
      zoom={9}
      className={className}
      style={{ height: '100%', width: '100%' }}
      zoomControl={true}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/">CARTO</a>'
        maxZoom={18}
      />

      <FlyToAOI aoi={aoi} />

      {/* AOI boundary */}
      {aoi && (
        <GeoJSON
          key={aoi.id}
          data={aoi.geometry as GeoJSON.GeoJsonObject}
          style={{ color: '#3b82f6', weight: 1.5, opacity: 0.4, fillOpacity: 0.04, fillColor: '#3b82f6' }}
        />
      )}

      {/* Observations layer */}
      {activeLayers.has('observations') && (
        <LayerGroup>
          {observations.map((obs) => {
            const color = confidenceColor(obs.confidence)
            if (obs.geometry?.type === 'Point') {
              const [lng, lat] = (obs.geometry.coordinates as [number, number])
              return (
                <CircleMarker
                  key={obs.id}
                  center={[lat, lng]}
                  radius={6}
                  pathOptions={{ color, fillColor: color, fillOpacity: 0.7, weight: 1.5 }}
                  eventHandlers={{ click: () => onObservationClick?.(obs) }}
                >
                </CircleMarker>
              )
            }
            if (obs.geometry?.type === 'Polygon') {
              return (
                <GeoJSON
                  key={obs.id}
                  data={obs.geometry as GeoJSON.GeoJsonObject}
                  style={{ color, weight: 2, opacity: 0.9, fillColor: color, fillOpacity: 0.2 }}
                  eventHandlers={{ click: () => onObservationClick?.(obs) }}
                />
              )
            }
            return null
          })}
        </LayerGroup>
      )}

      {/* Trajectory frames */}
      {activeLayers.has('trajectory') && trajectoryFrames.length > 0 && (
        <LayerGroup>
          {trajectoryFrames.map((frame, i) => {
            const opacity = 0.06 + 0.28 * (i / Math.max(trajectoryFrames.length - 1, 1))
            return (
              <GeoJSON
                key={frame.id}
                data={frame.footprint as GeoJSON.GeoJsonObject}
                style={{ color: '#38bdf8', weight: 1, opacity: 0.5, fillColor: '#38bdf8', fillOpacity: opacity }}
              />
            )
          })}
        </LayerGroup>
      )}

      {/* Choke points */}
      {activeLayers.has('choke_points') && (
        <LayerGroup>
          {chokePoints.map((cp) => {
            const [lng, lat] = cp.location.coordinates
            const r = 4 + Math.round(cp.constriction_score * 8)
            return (
              <CircleMarker
                key={cp.id}
                center={[lat, lng]}
                radius={r}
                pathOptions={{
                  color: '#60a5fa',
                  fillColor: '#60a5fa',
                  fillOpacity: 0.4 + cp.constriction_score * 0.4,
                  weight: 1.5,
                }}
              />
            )
          })}
        </LayerGroup>
      )}
    </MapContainer>
  )
}
