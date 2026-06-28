// Typed fetch functions — one per API endpoint
import { api } from './client'
import type {
  HealthResponse, ReadyResponse, StatusResponse,
  AOIListResponse, AOISchema,
  ObservationListResponse,
  PredictionListResponse, ImpactListResponse,
  ChokePointListResponse, RiskPredictionListResponse,
  WaterbodyListResponse,
  AIReportResponse, ExplanationResponse,
  QueryRequest, QueryResponse,
} from './types'

// ── Meta ──────────────────────────────────────────────────────────────────────
export const fetchHealth  = () => api.get<HealthResponse>('/health')
export const fetchReady   = () => api.get<ReadyResponse>('/ready')
export const fetchStatus  = () => api.get<StatusResponse>('/status')

// ── AOIs ─────────────────────────────────────────────────────────────────────
export const fetchAOIs = () => api.get<AOIListResponse>('/aois')
export const fetchAOI  = (id: string) => api.get<AOISchema>(`/aois/${id}`)

// ── Observations ──────────────────────────────────────────────────────────────
export const fetchObservations = (
  aoiId: string,
  params?: { status?: string; obs_type?: string },
) => {
  const qs = new URLSearchParams()
  if (params?.status)   qs.set('status', params.status)
  if (params?.obs_type) qs.set('obs_type', params.obs_type)
  const q = qs.toString() ? `?${qs}` : ''
  return api.get<ObservationListResponse>(`/aois/${aoiId}/observations${q}`)
}

// ── Predictions / Impact ──────────────────────────────────────────────────────
export const fetchPredictions = (aoiId: string) =>
  api.get<PredictionListResponse>(`/aois/${aoiId}/predictions`)

export const fetchImpact = (aoiId: string) =>
  api.get<ImpactListResponse>(`/aois/${aoiId}/impact`)

// ── Hydro ─────────────────────────────────────────────────────────────────────
export const fetchChokePoints = (aoiId: string) =>
  api.get<ChokePointListResponse>(`/aois/${aoiId}/choke-points`)

export const fetchFloodRisk = (aoiId: string) =>
  api.get<RiskPredictionListResponse>(`/aois/${aoiId}/flood-risk`)

export const fetchAcidRisk = (aoiId: string) =>
  api.get<RiskPredictionListResponse>(`/aois/${aoiId}/acid-risk`)

// ── Water Bodies ──────────────────────────────────────────────────────────────
export const fetchWaterbodies = () =>
  api.get<WaterbodyListResponse>('/waterbodies')

export const fetchWQObservations = (targetId: string, obsType?: string) => {
  const qs = obsType ? `?obs_type=${obsType}` : ''
  return api.get<ObservationListResponse>(`/waterbody/${targetId}/observations${qs}`)
}

export const fetchWQForecasts = (targetId: string) =>
  api.get<PredictionListResponse>(`/waterbody/${targetId}/forecasts`)

export const fetchWQAnomalies = (targetId: string) =>
  api.get<PredictionListResponse>(`/waterbody/${targetId}/anomalies`)

export const fetchWQReport = (targetId: string) =>
  api.get<AIReportResponse>(`/waterbody/${targetId}/report`)

// ── AI ────────────────────────────────────────────────────────────────────────
export const fetchExplanation = (predId: string) =>
  api.get<ExplanationResponse>(`/anomaly/${predId}/explanation`)

export const postNLQuery = (body: QueryRequest) =>
  api.post<QueryResponse>('/query', body)
