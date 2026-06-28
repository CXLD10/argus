// Canonical API response types — derived from argus/api/schemas.py
// Do not add fields not present in the backend schemas.

export interface HealthResponse {
  status: string
  version: string
}

export interface ReadyResponse {
  status: 'ready' | 'not_ready'
  reason: string | null
}

export interface QuotaStatus {
  cdse_bytes_today: number
  cdse_daily_limit_gb: number
  cdse_remaining_bytes: number
}

export interface RunSummary {
  domain_id: string
  aoi_id: string
  last_run_at: string | null
  last_run_status: string | null
  scenes_fetched: number
  observations_created: number
  bytes_used: number
}

export interface StatusResponse {
  version: string
  store_accessible: boolean
  last_analysis_run_at: string | null
  quota: QuotaStatus
  domain_runs: RunSummary[]
  open_meteo_calls_today: number
}

export type GeoJSONGeometry =
  | { type: 'Point'; coordinates: [number, number] }
  | { type: 'Polygon'; coordinates: [number, number][][] }
  | { type: 'MultiPolygon'; coordinates: [number, number][][][]}
  | { type: 'LineString'; coordinates: [number, number][] }

export interface AOISchema {
  id: string
  name: string
  geometry: GeoJSONGeometry
  domains: string[]
  active: boolean
}

export interface AOIListResponse {
  items: AOISchema[]
  count: number
}

export interface ObservationSchema {
  id: string
  analysis_run_id: string
  scene_id: string
  obs_type: string
  evidence_class: 'measured' | 'modeled' | 'inferred'
  geometry: GeoJSONGeometry
  area_km2: number
  confidence: number
  status: 'candidate' | 'confirmed' | 'dismissed' | 'archived'
  created_at: string
  value?: number | null
  unit?: string | null
  domain?: string
  target_id?: string | null
  attrs?: Record<string, unknown>
}

export interface ObservationListResponse {
  items: ObservationSchema[]
  count: number
}

export interface ForecastFrameSchema {
  id: string
  prediction_id: string
  valid_at: string
  footprint: GeoJSONGeometry
  particle_count: number
  stats: Record<string, unknown>
}

export interface PredictionSchema {
  id: string
  predictor_id: string
  kind: string
  evidence_class: string
  uncertainty: Record<string, unknown>
  created_at: string
  frames: ForecastFrameSchema[]
}

export interface PredictionListResponse {
  items: PredictionSchema[]
  count: number
  _attribution?: string
}

export interface ImpactAssessmentSchema {
  id: string
  prediction_id: string
  exposure_layer_id: string
  valid_at: string
  eta_hours: number
  metrics: Record<string, unknown>
}

export interface ImpactListResponse {
  items: ImpactAssessmentSchema[]
  count: number
  _attribution?: string
}

export interface ChokePointSchema {
  id: string
  aoi_id: string
  location: { type: 'Point'; coordinates: [number, number] }
  upstream_area_km2: number
  constriction_score: number
  dem_source: string
  evidence_class: string
}

export interface ChokePointListResponse {
  items: ChokePointSchema[]
  count: number
}

export interface RiskPredictionSchema {
  id: string
  predictor_id: string
  kind: string
  evidence_class: string
  label: string
  risk_score: number | null
  risk_level: 'low' | 'medium' | 'high' | 'extreme' | null
  acid_risk_index: number | null
  uncertainty: Record<string, unknown>
  created_at: string
}

export interface RiskPredictionListResponse {
  items: RiskPredictionSchema[]
  count: number
}

export interface WaterbodyListResponse {
  target_ids: string[]
  count: number
}

export interface AIReportResponse {
  text: string
  citations: string[]
  model: string
  _attribution?: string
}

export interface ExplanationResponse {
  hypothesis: string
  advisory: string
  confidence: string
  citations: string[]
  model: string
  _attribution?: string
}

export interface QueryRequest {
  question: string
}

export interface QueryResponse {
  answer: string
  citations: string[]
  model: string
  _attribution?: string
}

// Domain helper types
export type RiskLevel = 'low' | 'medium' | 'high' | 'extreme'
export type EvidenceClass = 'measured' | 'modeled' | 'inferred'
export type ObsStatus = 'candidate' | 'confirmed' | 'dismissed' | 'archived'
export type DomainId = 'marine_oil' | 'inland_wq' | 'weather_hydro' | 'hydro_chokepoints'
