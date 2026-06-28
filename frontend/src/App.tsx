import { Routes, Route } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { Overview } from '@/pages/Overview'
import { MapPage } from '@/pages/MapPage'
import { OilMonitoringPage } from '@/pages/OilMonitoringPage'
import { WaterQualityPage } from '@/pages/WaterQualityPage'
import { HydroPage } from '@/pages/HydroPage'
import { ChokePointsPage } from '@/pages/ChokePointsPage'
import { AlertsPage } from '@/pages/AlertsPage'
import { PredictionsPage } from '@/pages/PredictionsPage'
import { AIAssistantPage } from '@/pages/AIAssistantPage'
import { ExportsPage } from '@/pages/ExportsPage'
import { AdminPage } from '@/pages/AdminPage'
import { SettingsPage } from '@/pages/SettingsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Overview />} />
        <Route path="map" element={<MapPage />} />
        <Route path="oil" element={<OilMonitoringPage />} />
        <Route path="water-quality" element={<WaterQualityPage />} />
        <Route path="hydro" element={<HydroPage />} />
        <Route path="choke-points" element={<ChokePointsPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="predictions" element={<PredictionsPage />} />
        <Route path="ai" element={<AIAssistantPage />} />
        <Route path="exports" element={<ExportsPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
