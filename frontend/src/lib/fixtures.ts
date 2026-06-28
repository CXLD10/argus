// Demo-mode fixture data — used when the backend returns empty or is unreachable.
// Provides realistic data for presentations and demos.

import type {
  AOISchema, ObservationSchema, RiskPredictionSchema,
  ChokePointSchema, StatusResponse, AIReportResponse, QueryResponse,
} from '@/api/types'

export const DEMO_AOI: AOISchema = {
  id: 'gulf-paria-trinidad',
  name: 'Gulf of Paria — Trinidad',
  geometry: {
    type: 'Polygon',
    coordinates: [[
      [-62.0, 10.0], [-60.9, 10.0], [-60.9, 11.5], [-62.0, 11.5], [-62.0, 10.0],
    ]],
  },
  domains: ['marine_oil', 'inland_wq', 'weather_hydro', 'hydro_chokepoints'],
  active: true,
}

const now = () => new Date().toISOString()
const hoursAgo = (h: number) => new Date(Date.now() - h * 3600_000).toISOString()

export const DEMO_OBSERVATIONS: ObservationSchema[] = [
  {
    id: 'obs-oil-001',
    analysis_run_id: 'run-001',
    scene_id: 'S1A_IW_20240605T100000',
    obs_type: 'oil_slick',
    evidence_class: 'measured',
    geometry: { type: 'Polygon', coordinates: [[
      [-61.35, 10.62], [-61.25, 10.62], [-61.25, 10.72], [-61.35, 10.72], [-61.35, 10.62],
    ]]},
    area_km2: 8.4,
    confidence: 0.91,
    status: 'confirmed',
    created_at: hoursAgo(3),
    domain: 'marine_oil',
  },
  {
    id: 'obs-oil-002',
    analysis_run_id: 'run-001',
    scene_id: 'S1A_IW_20240605T100000',
    obs_type: 'oil_slick',
    evidence_class: 'measured',
    geometry: { type: 'Point', coordinates: [-61.48, 10.55] },
    area_km2: 2.1,
    confidence: 0.74,
    status: 'confirmed',
    created_at: hoursAgo(5),
    domain: 'marine_oil',
  },
  {
    id: 'obs-chl-001',
    analysis_run_id: 'run-002',
    scene_id: 'S2B_20240604T143200',
    obs_type: 'chlorophyll_a',
    evidence_class: 'measured',
    geometry: { type: 'Point', coordinates: [-61.18, 10.75] },
    area_km2: 0,
    confidence: 0.88,
    status: 'confirmed',
    created_at: hoursAgo(8),
    value: 42.3,
    unit: 'mg/m³',
    domain: 'inland_wq',
    target_id: 'wb-caroni-swamp',
  },
  {
    id: 'obs-chl-002',
    analysis_run_id: 'run-002',
    scene_id: 'S2B_20240604T143200',
    obs_type: 'chlorophyll_a',
    evidence_class: 'measured',
    geometry: { type: 'Point', coordinates: [-61.19, 10.74] },
    area_km2: 0,
    confidence: 0.85,
    status: 'confirmed',
    created_at: hoursAgo(12),
    value: 38.7,
    unit: 'mg/m³',
    domain: 'inland_wq',
    target_id: 'wb-caroni-swamp',
  },
  {
    id: 'obs-turb-001',
    analysis_run_id: 'run-002',
    scene_id: 'S2B_20240604T143200',
    obs_type: 'turbidity',
    evidence_class: 'measured',
    geometry: { type: 'Point', coordinates: [-61.20, 10.76] },
    area_km2: 0,
    confidence: 0.79,
    status: 'confirmed',
    created_at: hoursAgo(10),
    value: 18.4,
    unit: 'NTU',
    domain: 'inland_wq',
    target_id: 'wb-caroni-swamp',
  },
  {
    id: 'obs-precip-001',
    analysis_run_id: 'run-003',
    scene_id: 'open-meteo-forecast',
    obs_type: 'precipitation',
    evidence_class: 'modeled',
    geometry: { type: 'Point', coordinates: [-61.26, 10.65] },
    area_km2: 0,
    confidence: 0.95,
    status: 'confirmed',
    created_at: hoursAgo(1),
    value: 87.2,
    unit: 'mm/24h',
    domain: 'weather_hydro',
  },
]

export const DEMO_FLOOD_RISK: RiskPredictionSchema = {
  id: 'pred-flood-001',
  predictor_id: 'flood_risk',
  kind: 'flood_risk',
  evidence_class: 'modeled',
  label: 'Flood Risk · Gulf of Paria',
  risk_score: 0.71,
  risk_level: 'high',
  acid_risk_index: null,
  uncertainty: { p10: 0.58, p90: 0.84, method: 'bootstrap' },
  created_at: hoursAgo(1),
}

export const DEMO_ACID_RISK: RiskPredictionSchema = {
  id: 'pred-acid-001',
  predictor_id: 'acid_deposition',
  kind: 'acid_deposition_risk',
  evidence_class: 'modeled',
  label: 'Acid Deposition Risk Index',
  risk_score: null,
  risk_level: null,
  acid_risk_index: 6.8,
  uncertainty: { p10: 5.9, p90: 7.4, method: 'monte_carlo' },
  created_at: hoursAgo(2),
}

export const DEMO_CHOKE_POINTS: ChokePointSchema[] = [
  {
    id: 'cp-caroni-01',
    aoi_id: 'gulf-paria-trinidad',
    location: { type: 'Point', coordinates: [-61.38, 10.62] },
    upstream_area_km2: 1247.3,
    constriction_score: 0.87,
    dem_source: 'Copernicus DEM GLO-30',
    evidence_class: 'inferred',
  },
  {
    id: 'cp-north-coast-01',
    aoi_id: 'gulf-paria-trinidad',
    location: { type: 'Point', coordinates: [-61.21, 10.82] },
    upstream_area_km2: 634.1,
    constriction_score: 0.61,
    dem_source: 'Copernicus DEM GLO-30',
    evidence_class: 'inferred',
  },
  {
    id: 'cp-south-01',
    aoi_id: 'gulf-paria-trinidad',
    location: { type: 'Point', coordinates: [-61.52, 10.18] },
    upstream_area_km2: 389.8,
    constriction_score: 0.45,
    dem_source: 'Copernicus DEM GLO-30',
    evidence_class: 'inferred',
  },
]

export const DEMO_STATUS: StatusResponse = {
  version: '1.0.0-demo',
  store_accessible: true,
  last_analysis_run_at: hoursAgo(1),
  quota: {
    cdse_bytes_today: 284_000_000,
    cdse_daily_limit_gb: 1,
    cdse_remaining_bytes: 716_000_000,
  },
  domain_runs: [
    {
      domain_id: 'marine_oil',
      aoi_id: 'gulf-paria-trinidad',
      last_run_at: hoursAgo(3),
      last_run_status: 'complete',
      scenes_fetched: 4,
      observations_created: 2,
      bytes_used: 142_000_000,
    },
    {
      domain_id: 'inland_wq',
      aoi_id: 'gulf-paria-trinidad',
      last_run_at: hoursAgo(8),
      last_run_status: 'complete',
      scenes_fetched: 2,
      observations_created: 3,
      bytes_used: 98_000_000,
    },
    {
      domain_id: 'weather_hydro',
      aoi_id: 'gulf-paria-trinidad',
      last_run_at: hoursAgo(1),
      last_run_status: 'complete',
      scenes_fetched: 8,
      observations_created: 12,
      bytes_used: 44_000_000,
    },
    {
      domain_id: 'hydro_chokepoints',
      aoi_id: 'gulf-paria-trinidad',
      last_run_at: hoursAgo(24),
      last_run_status: 'complete',
      scenes_fetched: 1,
      observations_created: 3,
      bytes_used: 0,
    },
  ],
  open_meteo_calls_today: 847,
}

export const DEMO_AI_REPORT: AIReportResponse = {
  text: `Monitoring of the Gulf of Paria AOI over the past 24 hours indicates elevated environmental risk across two domains.

Two oil slick signatures have been confirmed from Sentinel-1 SAR imagery: a primary slick of 8.4 km² (91% confidence) and a secondary feature of 2.1 km². Both are consistent with chronic vessel discharge rather than an acute spill event, based on slick morphology and wind-corrected drift modelling.

Caroni Swamp water quality data shows chlorophyll-a at 42.3 mg/m³ — approximately 2.8× the seasonal baseline, consistent with an active cyanobacterial bloom phase. Turbidity is elevated at 18.4 NTU. The combination of high nutrients and reduced water exchange creates conditions favourable for further bloom intensification over the next 3–5 days.

Flood risk for this AOI is scored HIGH (0.71) based on 87.2 mm/24h forecast precipitation driving elevated GloFAS discharge projections at the primary choke point.`,
  citations: [
    'obs-oil-001',
    'obs-oil-002',
    'obs-chl-001',
    'obs-precip-001',
    'pred-flood-001',
  ],
  model: 'template-v1 (grounded)',
  _attribution: 'Argus AI · Grounded in platform observations only',
}

export const DEMO_NL_RESPONSE: QueryResponse = {
  answer: 'The highest constriction score belongs to the Caroni choke point (cp-caroni-01) with a score of 0.87 and upstream drainage area of 1,247 km². This is a high-priority monitoring location given the current high flood risk score of 0.71.',
  citations: ['cp-caroni-01', 'pred-flood-001'],
  model: 'template-v1 (grounded)',
  _attribution: 'Argus AI · Advisory only',
}
