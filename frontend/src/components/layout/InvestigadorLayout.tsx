import { Outlet } from 'react-router-dom'
import { LayoutDashboard, Bot, History } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'

const investigadorItems: SidebarItem[] = [
  { label: 'Dashboard', href: '/investigador', icon: LayoutDashboard },
  { label: 'Demo Multiagente', href: '/swarm-demo', icon: Bot },
  { label: 'Replay Cognitivo', href: '/replay', icon: History },
]

export default function InvestigadorLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
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
