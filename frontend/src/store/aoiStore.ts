import { create } from 'zustand'
import type { AOISchema, ObservationSchema } from '@/api/types'

interface AOIState {
  selectedAOI: AOISchema | null
  selectedObservation: ObservationSchema | null
  setSelectedAOI: (aoi: AOISchema | null) => void
  setSelectedObservation: (obs: ObservationSchema | null) => void
}

export const useAOIStore = create<AOIState>((set) => ({
  selectedAOI: null,
  selectedObservation: null,
  setSelectedAOI: (aoi) => set({ selectedAOI: aoi, selectedObservation: null }),
  setSelectedObservation: (obs) => set({ selectedObservation: obs }),
}))
