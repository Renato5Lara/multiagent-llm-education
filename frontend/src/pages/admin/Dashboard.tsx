import { Link } from 'react-router-dom'
import { Users, GraduationCap, UserCheck, ShieldCheck, UserX, Activity, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { useUsers } from '@/hooks/useUsers'
import { useSystemHealth } from '@/hooks/useSystemHealth'
import { getRoleLabel, getRoleBadgeColor, formatDate } from '@/lib/utils'
import PageHeader from '@/components/common/PageHeader'

export default function AdminDashboard() {
    // include_inactive: el admin necesita ver cuentas desactivadas para
    // responder "¿cuántas cuentas están desactivadas?", no solo las activas.
    const { data: usersData, isLoading: loadingUsers } = useUsers({ page: 1, size: 100, include_inactive: true })
    const { data: health } = useSystemHealth()

    const users = usersData?.users ?? []
    const totalUsers = users.length
    const totalDocentes = users.filter(u => u.role === 'docente').length
    const totalEstudiantes = users.filter(u => u.role === 'estudiante').length
    const totalAdmins = users.filter(u => u.role === 'admin').length
    const totalInactive = users.filter(u => !u.is_active).length

    const recentUsers = [...users]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5)

    const kpis = [
        { label: 'Total Usuarios', value: totalUsers, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
        { label: 'Docentes', value: totalDocentes, icon: GraduationCap, color: 'text-emerald-600', bg: 'bg-emerald-50' },
        { label: 'Estudiantes', value: totalEstudiantes, icon: UserCheck, color: 'text-purple-600', bg: 'bg-purple-50' },
        { label: 'Administradores', value: totalAdmins, icon: ShieldCheck, color: 'text-cyan-600', bg: 'bg-cyan-50' },
        { label: 'Cuentas Desactivadas', value: totalInactive, icon: UserX, color: 'text-red-600', bg: 'bg-red-50' },
    ]

    return (
        <div>
            <PageHeader title="Panel de Administración" description="Usuarios, roles y estado de la plataforma" />

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5 mb-8">
                {kpis.map((kpi) => (
                    <Card key={kpi.label} className="border shadow-sm hover:shadow-md transition-shadow">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-medium text-muted-foreground">{kpi.label}</p>
                                    {loadingUsers ? (
                                        <Skeleton className="h-8 w-16 mt-1" />
                                    ) : (
                                        <p className="text-3xl font-bold mt-1">{kpi.value}</p>
                                    )}
                                </div>
                                <div className={`h-12 w-12 rounded-xl ${kpi.bg} flex items-center justify-center`}>
                                    <kpi.icon className={`h-6 w-6 ${kpi.color}`} />
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <div className="grid gap-4 md:grid-cols-2 mb-8">
                <Link to="/admin/system">
                    <Card className="hover:shadow-md transition-shadow h-full">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle className="text-lg flex items-center gap-2"><Activity className="h-5 w-5 text-primary" />Estado del sistema</CardTitle>
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <Badge variant="secondary" className={health?.status === 'ok' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}>
                                {health?.status === 'ok' ? 'Todo operativo' : health ? 'Degradado' : 'Verificando...'}
                            </Badge>
                            <p className="text-xs text-muted-foreground mt-2">Base de datos, IA, investigación y enjambre multiagente.</p>
                        </CardContent>
                    </Card>
                </Link>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Últimos registros</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {loadingUsers ? (
                            <div className="space-y-3">
                                {[...Array(5)].map((_, i) => (
                                    <Skeleton key={i} className="h-12 w-full" />
                                ))}
                            </div>
                        ) : recentUsers.length === 0 ? (
                            <p className="text-muted-foreground text-sm text-center py-8">No hay usuarios registrados</p>
                        ) : (
                            <div className="divide-y">
                                {recentUsers.map((user) => (
                                    <div key={user.id} className="flex items-center justify-between py-3">
                                        <div className="flex items-center gap-3">
                                            <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center text-sm font-semibold text-primary">
                                                {user.first_name.charAt(0)}{user.last_name.charAt(0)}
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium">{user.first_name} {user.last_name}</p>
                                                <p className="text-xs text-muted-foreground">{user.email}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <Badge variant="secondary" className={getRoleBadgeColor(user.role)}>
                                                {getRoleLabel(user.role)}
                                            </Badge>
                                            <span className="text-xs text-muted-foreground">{formatDate(user.created_at)}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
