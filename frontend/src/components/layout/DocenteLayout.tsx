import { Outlet } from 'react-router-dom'
import { LayoutDashboard, BookOpen, BarChart3 } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'

const docenteItems: SidebarItem[] = [
  { label: 'Dashboard', href: '/docente', icon: LayoutDashboard },
  { label: 'Mis Cursos', href: '/docente/courses', icon: BookOpen },
  { label: 'Analítica IA', href: '/docente/analytics', icon: BarChart3 },
]

export default function DocenteLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
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
