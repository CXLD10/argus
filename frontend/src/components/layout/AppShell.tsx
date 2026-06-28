import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

export function AppShell() {
  const location = useLocation()

  return (
    <div className="flex h-screen overflow-hidden bg-[#080c14]">
      {/* Skip navigation for accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-blue-600 focus:text-white focus:px-3 focus:py-1.5 focus:rounded-lg focus:text-sm focus:font-medium"
      >
        Skip to main content
      </a>

      <Sidebar />

      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        <Header />
        <main
          id="main-content"
          className="flex-1 overflow-auto"
          role="main"
          aria-label="Main content"
          key={location.pathname}
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}
