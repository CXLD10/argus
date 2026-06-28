import { create } from 'zustand'

interface UIState {
  sidebarCollapsed: boolean
  activePanel: string | null   // 'detail' | 'ai' | 'export' | null
  setSidebarCollapsed: (v: boolean) => void
  toggleSidebar: () => void
  setActivePanel: (panel: string | null) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  activePanel: null,
  setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setActivePanel: (panel) => set({ activePanel: panel }),
}))
