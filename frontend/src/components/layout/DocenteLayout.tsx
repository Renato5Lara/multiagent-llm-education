import { Outlet } from 'react-router-dom'
import { LayoutDashboard, BookOpen } from 'lucide-react'
import Sidebar, { SidebarItem } from './Sidebar'
import Header from './Header'

const docenteItems: SidebarItem[] = [
    { label: 'Dashboard', href: '/docente', icon: LayoutDashboard },
    { label: 'Mis Cursos', href: '/docente/courses', icon: BookOpen },
]

export default function DocenteLayout() {
    return (
        <div className="min-h-screen bg-gray-50">
            <Sidebar items={docenteItems} />
            <div className="ml-64">
                <Header />
                <main className="p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    )
}
