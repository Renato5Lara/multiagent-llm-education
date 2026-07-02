import { Outlet } from 'react-router-dom'
import { LayoutDashboard, Users, Shield, FlaskConical } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'

const adminItems: SidebarItem[] = [
  { label: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { label: 'Usuarios', href: '/admin/users', icon: Users },
  { label: 'Roles', href: '/admin/roles', icon: Shield },
  { label: 'Modo Evidencia', href: '/evidencia', icon: FlaskConical, sectionBefore: true },
]

export default function AdminLayout() {
  return (
    <div className="min-h-screen bg-neural-surface">
      <Sidebar items={adminItems} />
      <div className="lg:ml-64">
        <Header />
        <main className="p-4 md:p-6 pt-16 lg:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
