import { Outlet } from 'react-router-dom'
import { LayoutDashboard, BookOpen, BarChart3, GitCompare, FlaskConical } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'

const docenteItems: SidebarItem[] = [
  { label: 'Dashboard', href: '/docente', icon: LayoutDashboard },
  { label: 'Mis Cursos', href: '/docente/courses', icon: BookOpen },
  { label: 'Analítica IA', href: '/docente/analytics', icon: BarChart3 },
  { label: 'Comparación Swarm', href: '/docente/swarm-comparison', icon: GitCompare },
  { label: 'Modo Evidencia', href: '/evidencia', icon: FlaskConical, sectionBefore: true },
]

export default function DocenteLayout() {
  return (
    <div className="min-h-screen bg-neural-surface">
      <Sidebar items={docenteItems} />
      <div className="lg:ml-64">
        <Header />
        <main className="p-4 md:p-6 pt-16 lg:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
