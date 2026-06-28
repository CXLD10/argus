import { cn } from '@/lib/utils'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Map, Droplets, Activity, CloudRain, Triangle,
  Bell, TrendingUp, Bot, FileDown, Settings, ShieldCheck,
  ChevronLeft, ChevronRight, Waves,
} from 'lucide-react'
import { useUIStore } from '@/store/uiStore'

interface NavItem {
  label: string
  to: string
  icon: React.ComponentType<{ className?: string }>
  group: string
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Overview',         to: '/',              icon: LayoutDashboard, group: 'main' },
  { label: 'Live Map',         to: '/map',           icon: Map,             group: 'main' },
  { label: 'Oil Monitoring',   to: '/oil',           icon: Droplets,        group: 'domains' },
  { label: 'Water Quality',    to: '/water-quality', icon: Activity,        group: 'domains' },
  { label: 'Weather & Hydro',  to: '/hydro',         icon: CloudRain,       group: 'domains' },
  { label: 'Choke Points',     to: '/choke-points',  icon: Triangle,        group: 'domains' },
  { label: 'Alerts',           to: '/alerts',        icon: Bell,            group: 'monitor' },
  { label: 'Predictions',      to: '/predictions',   icon: TrendingUp,      group: 'monitor' },
  { label: 'AI Assistant',     to: '/ai',            icon: Bot,             group: 'intel' },
  { label: 'Reports',          to: '/exports',       icon: FileDown,        group: 'intel' },
  { label: 'Admin',            to: '/admin',         icon: ShieldCheck,     group: 'system' },
  { label: 'Settings',         to: '/settings',      icon: Settings,        group: 'system' },
]

const GROUP_LABELS: Record<string, string> = {
  main:    '',
  domains: 'Domains',
  monitor: 'Monitoring',
  intel:   'Intelligence',
  system:  'System',
}

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const location = useLocation()

  const groups = ['main', 'domains', 'monitor', 'intel', 'system']

  return (
    <aside
      className={cn(
        'relative flex flex-col bg-[#090d1a] transition-[width] duration-200 ease-out shrink-0',
        'border-r border-[#0f1a2a]',
        sidebarCollapsed ? 'w-[52px]' : 'w-[220px]',
      )}
    >
      {/* Logo */}
      <div className={cn(
        'flex h-[52px] items-center border-b border-[#0f1a2a] shrink-0',
        sidebarCollapsed ? 'justify-center px-3' : 'gap-3 px-4',
      )}>
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-600 shadow-[0_0_12px_rgba(59,130,246,0.3)]">
          <Waves className="h-3.5 w-3.5 text-white" />
        </div>
        {!sidebarCollapsed && (
          <div className="min-w-0">
            <p className="text-sm font-bold text-white leading-none tracking-tight">ARGUS</p>
            <p className="text-[10px] text-slate-600 leading-none mt-0.5 font-medium tracking-wide">ENVIRONMENTAL INTEL</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden py-3 px-2" aria-label="Main navigation">
        {groups.map((group) => {
          const items = NAV_ITEMS.filter((i) => i.group === group)
          const label = GROUP_LABELS[group]
          return (
            <div key={group} className="mb-4 last:mb-0">
              {label && !sidebarCollapsed && (
                <p className="px-2 pb-1 pt-0.5 text-label text-slate-600">
                  {label}
                </p>
              )}
              <div className="space-y-0.5">
                {items.map((item) => {
                  const Icon = item.icon
                  const isActive = item.to === '/'
                    ? location.pathname === '/'
                    : location.pathname.startsWith(item.to)

                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      aria-label={sidebarCollapsed ? item.label : undefined}
                      title={sidebarCollapsed ? item.label : undefined}
                      className={cn(
                        'relative flex items-center rounded-lg text-sm transition-all duration-150',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                        sidebarCollapsed ? 'justify-center px-0 py-2 h-9' : 'gap-2.5 px-2.5 py-2',
                        isActive
                          ? 'bg-blue-600/12 text-blue-400 font-medium'
                          : 'text-slate-500 hover:bg-[#141d2e] hover:text-slate-300',
                      )}
                    >
                      {isActive && (
                        <span className="nav-item-active-bar" aria-hidden="true" />
                      )}
                      <Icon className={cn(
                        'shrink-0 transition-colors',
                        sidebarCollapsed ? 'h-4.5 w-4.5' : 'h-4 w-4',
                        isActive ? 'text-blue-400' : 'text-slate-600 group-hover:text-slate-400',
                      )} />
                      {!sidebarCollapsed && (
                        <span className="truncate">{item.label}</span>
                      )}
                    </NavLink>
                  )
                })}
              </div>
            </div>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="shrink-0 border-t border-[#0f1a2a] p-2 space-y-1">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-[#141d2e] cursor-pointer transition-colors">
            <div className="h-6 w-6 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-[10px] font-bold text-white shrink-0 shadow-sm">
              J
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-slate-300 leading-none truncate">Josh Admin</p>
              <p className="text-[10px] text-slate-600 leading-none mt-0.5">Administrator</p>
            </div>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={cn(
            'flex w-full items-center justify-center rounded-lg py-1.5 text-slate-600',
            'hover:bg-[#141d2e] hover:text-slate-400 transition-colors',
            sidebarCollapsed ? 'px-0' : 'gap-1.5 px-2',
          )}
        >
          {sidebarCollapsed
            ? <ChevronRight className="h-3.5 w-3.5" />
            : <><ChevronLeft className="h-3.5 w-3.5" /><span className="text-xs">Collapse</span></>
          }
        </button>
      </div>
    </aside>
  )
}
