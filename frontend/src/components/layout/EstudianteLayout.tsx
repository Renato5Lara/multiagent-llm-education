import { Outlet } from 'react-router-dom'
import { LayoutDashboard, BarChart3 } from 'lucide-react'
import Sidebar, { SidebarItem } from './Sidebar'
import Header from './Header'

const estudianteItems: SidebarItem[] = [
    { label: 'Dashboard', href: '/estudiante', icon: LayoutDashboard },
    { label: 'Progreso', href: '/estudiante/progress', icon: BarChart3 },
]

export default function EstudianteLayout() {
    return (
        <div className="min-h-screen bg-gray-50">
            <Sidebar items={estudianteItems} />
            <div className="ml-64">
                <Header />
                <main className="p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    )
}
