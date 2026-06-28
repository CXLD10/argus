import { cn } from '@/lib/utils'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Map, Droplets, CloudRain, Triangle,
  Bell, TrendingUp, Bot, FileDown, Settings, ShieldCheck,
  ChevronLeft, ChevronRight,
} from 'lucide-react'
import { useUIStore } from '@/store/uiStore'

interface NavItem {
  label: string
  to: string
  icon: React.ComponentType<{ className?: string }>
  group?: string
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Overview',      to: '/',             icon: LayoutDashboard, group: 'main' },
  { label: 'Map',           to: '/map',          icon: Map,             group: 'main' },
  { label: 'Oil Monitoring',to: '/oil',          icon: Droplets,        group: 'domains' },
  { label: 'Water Quality', to: '/water-quality',icon: Droplets,        group: 'domains' },
  { label: 'Weather & Hydro', to: '/hydro',      icon: CloudRain,       group: 'domains' },
  { label: 'Choke Points',  to: '/choke-points', icon: Triangle,        group: 'domains' },
  { label: 'Alerts',        to: '/alerts',       icon: Bell,            group: 'monitor' },
  { label: 'Predictions',   to: '/predictions',  icon: TrendingUp,      group: 'monitor' },
  { label: 'AI Assistant',  to: '/ai',           icon: Bot,             group: 'ai' },
  { label: 'Reports & Exports', to: '/exports',  icon: FileDown,        group: 'ai' },
  { label: 'Admin',         to: '/admin',        icon: ShieldCheck,     group: 'admin' },
  { label: 'Settings',      to: '/settings',     icon: Settings,        group: 'admin' },
]

const GROUP_LABELS: Record<string, string> = {
  main:    '',
  domains: 'Domains',
  monitor: 'Monitoring',
  ai:      'Intelligence',
  admin:   'System',
}

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const location = useLocation()

  const groups = Array.from(new Set(NAV_ITEMS.map((i) => i.group ?? '')))

  return (
    <aside
      className={cn(
        'relative flex flex-col border-r border-slate-800 bg-[#0d1424] transition-all duration-200',
        sidebarCollapsed ? 'w-14' : 'w-60',
      )}
    >
      {/* Logo */}
      <div className={cn(
        'flex h-14 items-center border-b border-slate-800 px-3 shrink-0',
        sidebarCollapsed ? 'justify-center' : 'gap-2',
      )}>
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-600">
          <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 text-white">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        {!sidebarCollapsed && (
          <div className="min-w-0">
            <p className="text-sm font-bold text-slate-100 leading-none">ARGUS</p>
            <p className="text-[10px] text-slate-500 leading-none mt-0.5">Environmental Intelligence</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-4">
        {groups.map((group) => {
          const items = NAV_ITEMS.filter((i) => (i.group ?? '') === group)
          const label = GROUP_LABELS[group]
          return (
            <div key={group} className="space-y-0.5">
              {label && !sidebarCollapsed && (
                <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
                  {label}
                </p>
              )}
              {items.map((item) => {
                const Icon = item.icon
                const isActive = item.to === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.to)
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    title={sidebarCollapsed ? item.label : undefined}
                    className={cn(
                      'flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm transition-colors',
                      'group relative',
                      isActive
                        ? 'bg-blue-600/20 text-blue-400 font-medium'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200',
                      sidebarCollapsed && 'justify-center px-2',
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
                    {isActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-r bg-blue-500" />
                    )}
                  </NavLink>
                )
              })}
            </div>
          )
        })}
      </nav>

      {/* User / Collapse */}
      <div className="shrink-0 border-t border-slate-800 p-2 space-y-1">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-800 cursor-pointer">
            <div className="h-6 w-6 rounded-full bg-blue-600 flex items-center justify-center text-[10px] font-bold text-white shrink-0">
              J
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-slate-200 leading-none truncate">Josh Admin</p>
              <p className="text-[10px] text-slate-500 leading-none mt-0.5">Administrator</p>
            </div>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition-colors"
        >
          {sidebarCollapsed
            ? <ChevronRight className="h-3.5 w-3.5" />
            : <><ChevronLeft className="h-3.5 w-3.5" /><span>Collapse</span></>
          }
        </button>
      </div>
    </aside>
  )
}
