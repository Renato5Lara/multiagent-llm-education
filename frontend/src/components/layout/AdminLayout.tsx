import { Outlet } from 'react-router-dom'
import { LayoutDashboard, Users, Shield } from 'lucide-react'
import Sidebar, { SidebarItem } from './Sidebar'
import Header from './Header'

const adminItems: SidebarItem[] = [
    { label: 'Dashboard', href: '/admin', icon: LayoutDashboard },
    { label: 'Usuarios', href: '/admin/users', icon: Users },
    { label: 'Roles', href: '/admin/roles', icon: Shield },
]

export default function AdminLayout() {
    return (
        <div className="min-h-screen bg-gray-50">
            <Sidebar items={adminItems} />
            <div className="ml-64">
                <Header />
                <main className="p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    )
}
