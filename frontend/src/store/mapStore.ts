import { create } from 'zustand'

type LayerId = 'observations' | 'trajectory' | 'choke_points' | 'flood_risk' | 'acid_risk' | 'wq'

interface MapState {
  activeLayers: Set<LayerId>
  viewport: { lat: number; lng: number; zoom: number }
  toggleLayer: (id: LayerId) => void
  setViewport: (v: { lat: number; lng: number; zoom: number }) => void
  isLayerActive: (id: LayerId) => boolean
}

const DEFAULT_LAYERS: LayerId[] = ['observations', 'trajectory', 'choke_points', 'wq']

export const useMapStore = create<MapState>((set, get) => ({
  activeLayers: new Set<LayerId>(DEFAULT_LAYERS),
  viewport: { lat: 11.15, lng: -61.25, zoom: 9 },
  toggleLayer: (id) =>
    set((s) => {
      const next = new Set(s.activeLayers)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return { activeLayers: next }
    }),
  setViewport: (v) => set({ viewport: v }),
  isLayerActive: (id) => get().activeLayers.has(id),
}))
