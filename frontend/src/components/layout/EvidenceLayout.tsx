import { Outlet } from 'react-router-dom'
import { FlaskConical, Bot, History } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'

const evidenceItems: SidebarItem[] = [
  { label: 'Modo Evidencia',   href: '/evidencia',  icon: FlaskConical },
  { label: 'Demo Multiagente', href: '/swarm-demo', icon: Bot },
  { label: 'Replay Cognitivo', href: '/replay',     icon: History },
]

export default function EvidenceLayout() {
  return (
    <div className="min-h-screen bg-neural-surface">
      <Sidebar items={evidenceItems} title="UPAO-MAS-EDU · Evidencia" />
      <div className="lg:ml-64">
        <Header />
        <main className="p-4 md:p-6 pt-16 lg:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
