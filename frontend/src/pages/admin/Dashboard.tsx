import { Users, GraduationCap, BookOpen, UserCheck } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { useUsers } from '@/hooks/useUsers'
import { useCourses } from '@/hooks/useCourses'
import { getRoleLabel, getRoleBadgeColor, formatDate } from '@/lib/utils'
import PageHeader from '@/components/common/PageHeader'

export default function AdminDashboard() {
    const { data: usersData, isLoading: loadingUsers } = useUsers({ page: 1, size: 100 })
    const { data: coursesData, isLoading: loadingCourses } = useCourses(1, 100)

    const users = usersData?.users ?? []
    const totalUsers = usersData?.total ?? 0
    const totalDocentes = users.filter(u => u.role === 'docente').length
    const totalEstudiantes = users.filter(u => u.role === 'estudiante').length
    const totalCourses = coursesData?.total ?? 0

    const estudiantes = users.filter(u => u.role === 'estudiante')
    const cycleDistribution = Array.from({ length: 10 }, (_, i) => i + 1).map(cycle => ({
        cycle,
        students: estudiantes.filter(e => e.current_cycle === cycle).length,
        courses: (coursesData?.courses ?? []).filter(c => c.cycle === cycle).length,
    }))

    const recentUsers = users.slice(0, 5)

    const kpis = [
        { label: 'Total Usuarios', value: totalUsers, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
        { label: 'Docentes', value: totalDocentes, icon: GraduationCap, color: 'text-emerald-600', bg: 'bg-emerald-50' },
        { label: 'Estudiantes', value: totalEstudiantes, icon: UserCheck, color: 'text-purple-600', bg: 'bg-purple-50' },
        { label: 'Cursos Activos', value: totalCourses, icon: BookOpen, color: 'text-amber-600', bg: 'bg-amber-50' },
    ]

    return (
        <div>
            <PageHeader title="Panel de Administración" description="Resumen general del sistema" />

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
                {kpis.map((kpi) => (
                    <Card key={kpi.label} className="border shadow-sm hover:shadow-md transition-shadow">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-medium text-muted-foreground">{kpi.label}</p>
                                    {loadingUsers || loadingCourses ? (
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
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Estudiantes por Ciclo</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {loadingUsers ? (
                            <div className="space-y-3">{[...Array(10)].map((_, i) => <Skeleton key={i} className="h-6 w-full" />)}</div>
                        ) : (
                            <div className="space-y-2">
                                {cycleDistribution.map(({ cycle, students, courses }) => (
                                    <div key={cycle} className="flex items-center justify-between py-2 border-b last:border-0">
                                        <span className="text-sm font-medium">Ciclo {cycle}</span>
                                        <div className="flex gap-4">
                                            <span className="text-xs text-muted-foreground">{students} estudiantes</span>
                                            <span className="text-xs text-muted-foreground">{courses} cursos</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>

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
