import { Outlet } from 'react-router-dom'
import { LayoutDashboard, Bot, History, FlaskConical, Activity, BarChart3, Settings } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'

const investigadorItems: SidebarItem[] = [
  { label: 'Dashboard',        href: '/investigador', icon: LayoutDashboard },
  { label: 'Demo Multiagente', href: '/swarm-demo',   icon: Bot },
  { label: 'Replay Cognitivo', href: '/replay',       icon: History },
  { label: 'Agent Lab',        href: '#',             icon: FlaskConical, disabled: true },
  { label: 'Swarm Monitor',    href: '#',             icon: Activity,     disabled: true },
  { label: 'Analytics',        href: '#',             icon: BarChart3,    disabled: true, sectionBefore: true },
  { label: 'Settings',         href: '#',             icon: Settings,     disabled: true },
]

export default function InvestigadorLayout() {
  return (
    <div className="min-h-screen bg-neural-surface">
      <Sidebar items={investigadorItems} title="UPAO-MAS-EDU · Demo" />
      <div className="lg:ml-64">
        <Header />
        <main className="p-4 md:p-6 pt-16 lg:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
